# Estratégia de Testes de Integração

## Decisão de Banco

### Banco escolhido: SQLite em memória (`sqlite+aiosqlite:///:memory:`)

**Motivo da escolha:**
- **Velocidade:** SQLite em memória é ordens de magnitude mais rápido que PostgreSQL em contêiner — cada banco é criado e destruído em microssegundos.
- **Isolamento:** Cada função de teste recebe um banco completamente novo, sem possibilidade de vazamento de estado entre testes rodando em paralelo ou sequencialmente.
- **Zero infraestrutura:** Nenhum serviço externo (Docker, PostgreSQL, Redis) é necessário para rodar os testes de integração — tudo roda in-process, simplificando CI e onboarding.
- **Consistência:** A estratégia é uniforme para todos os módulos do projeto — não é permitido misturar abordagens diferentes sem aprovação do Tech Lead.

**Driver:** `aiosqlite>=0.20.0` (já incluso em `requirements-dev.txt`)

### Escopo por função

```
scope="function"  ←  novo banco para cada função de teste
```

O escopo `function` garante isolamento absoluto: inserções no `test_A` nunca aparecem no `test_B`, mesmo que rodem no mesmo processo.

---

## Limitações Conhecidas

| Limitação | Impacto | Mitigação |
|-----------|---------|-----------|
| SQLite não suporta `FOR UPDATE` (SELECT ... FOR UPDATE) | Código que usa locking otimista pode falhar nos testes mas funcionar em produção | Evitar `FOR UPDATE` no ORM; testar com fixtures de concorrência separadas |
| SQLite usa tipagem dinâmica — `BOOLEAN` vira `INTEGER` | Campos booleanos funcionam, mas são armazenados como 0/1 | Assertions explícitas com `bool()` quando necessário |
| `server_default` do SQLAlchemy pode não disparar em SQLite da mesma forma que no PostgreSQL | Campos com `server_default=func.now()` podem retornar `None` após flush | Usar `expire_on_commit=False` + `await session.refresh(model)` para forçar leitura |
| Collation e ordenação podem diferir | Ordenações de string case-sensitive vs case-insensitive podem variar | Não depender de ordenação de strings case-sensitive nos testes |
| Sem suporte a `RETURNING` em algumas versões do SQLite | Statements de UPDATE/INSERT com RETURNING podem falhar | Usar `session.flush()` + `session.refresh()` em vez de RETURNING |

**Importante:** As limitações acima são aceitáveis para a suite de integração, que valida **contratos e comportamento de negócio**, não features específicas de PostgreSQL. Testes que exigem comportamento exclusivo do PostgreSQL devem ser marcados com `@pytest.mark.skip(reason="Requer PostgreSQL")`.

---

## Como Adicionar Testes de Integração

### 1. Estrutura de diretórios

```
tests/
├── conftest.py                    # fixtures globais (ai_response_fixture)
├── TESTING_STRATEGY.md            # este arquivo
├── fixtures/
│   └── ai_responses/
│       ├── generate_short_code.json
│       ├── analyze_url.json
│       └── workflow_complete.json
├── integration/
│   ├── conftest.py                # test_engine, test_db_session, client, etc.
│   ├── test_smoke_infra.py        # valida que a infra funciona
│   ├── test_url_crud.py           # CRUD de URLs
│   ├── test_tenant_isolation.py   # isolamento por session_id
│   ├── test_auth.py               # autenticação e autorização
│   └── test_agent_workflows.py    # fluxos de agente com IA mockada
└── unit/
    └── ...                        # testes unitários sem I/O real
```

### 2. Fixtures disponíveis

| Fixture | Onde | O que fornece |
|---------|------|---------------|
| `test_engine` | `integration/conftest.py` | AsyncEngine SQLite em memória |
| `test_db_session` | `integration/conftest.py` | AsyncSession conectada ao banco de teste |
| `app_with_db` | `integration/conftest.py` | FastAPI app com get_session overrideado |
| `client` | `integration/conftest.py` | AsyncClient HTTP sem rate limit, sem auth |
| `authenticated_client` | `integration/conftest.py` | AsyncClient com ApiKey válida no banco |
| `client_no_rate_limit` | `integration/conftest.py` | AsyncClient com ApiKey + rate limiter bypassed |
| `block_external_http` | `integration/conftest.py` | Bloqueia chamadas a GitHub, Jira, OpenAI, Anthropic |
| `ai_response_fixture` | `tests/conftest.py` | Carrega JSON de `tests/fixtures/ai_responses/` |
| `mock_url_repo` | `tests/conftest.py` | MockUrlRepository para testes unitários |
| `mock_api_key_repo` | `tests/conftest.py` | MockApiKeyRepository para testes unitários |

### 3. Template básico de teste de integração

```python
# tests/integration/test_minha_feature.py
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import ShortenedUrlModel

pytestmark = pytest.mark.asyncio


class TestMinhaFeature:
    """Descrição do que está sendo testado."""

    async def test_meu_cenario(
        self,
        client: AsyncClient,
        test_db_session: AsyncSession,
    ):
        # 1. Arrange — configurar estado inicial
        # 2. Act — executar a ação
        response = await client.post("/api/shorten", json={"url": "https://exemplo.com/"})

        # 3. Assert HTTP
        assert response.status_code in (200, 201)

        # 4. Assert banco — verificação dupla
        result = await test_db_session.execute(select(ShortenedUrlModel))
        urls = result.scalars().all()
        assert len(urls) == 1, f"Esperado 1 URL no banco, encontrado {len(urls)}"
```

### 4. Regras obrigatórias

1. **Sem mocks de repositório** nos testes de integração — use banco real (SQLite em memória)
2. **Sem chamadas HTTP reais** a serviços externos — use `block_external_http` e mocks explícitos
3. **Sem chamadas a APIs de IA reais** — use `ai_response_fixture` com arquivos JSON versionados
4. **Assertions em dupla camada** — verifique tanto o response HTTP quanto o estado no banco
5. **Mensagens descritivas** — inclua contexto nas assertions: `assert x == y, f"Esperado {y}, obtido {x}"`
6. **Escopo function** — não use `scope="session"` para dados de teste (apenas engine pode ter escopo maior se necessário)

### 5. Adicionando fixtures de IA

Para adicionar uma nova resposta de IA simulada:

1. Crie `tests/fixtures/ai_responses/minha_resposta.json` com o payload esperado
2. Use `ai_response_fixture("minha_resposta")` no teste
3. O JSON deve seguir o formato da API real que está sendo mockada (ex: OpenAI Chat Completions)
4. **Versione o arquivo junto ao código** — as fixtures de IA são parte do contrato testado
5. Revise as fixtures quando o comportamento esperado dos agentes mudar

---

## Execução no CI

```bash
# Rodar apenas testes de integração
pytest tests/integration/ -v --tb=short

# Rodar suite completa (deve completar em < 5 minutos)
pytest tests/ -v --tb=short

# Rodar com marcadores
pytest tests/ -m integration -v
pytest tests/ -m unit -v

# Rodar verificando cobertura
pytest tests/ --cov=app --cov-report=term-missing
```

**Requisito:** A suite completa deve completar em menos de 5 minutos no CI sem serviços externos.
