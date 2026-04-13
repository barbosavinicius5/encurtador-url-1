# encurtador-url-1

O Encurtador de URL é uma aplicação web que permite transformar URLs longas em links curtos e fáceis de compartilhar. O sistema também oferece métricas básicas de acesso, permitindo que o usuário visualize quantos cliques cada link recebeu.

## Testes E2E

Esta seção documenta como configurar e executar os testes end-to-end (E2E) do projeto.
Os testes E2E verificam os fluxos completos do sistema usando Playwright e um servidor real em ambiente Docker isolado.

> **Nota sobre testes Desktop (Tauri):** Os testes E2E para a aplicação desktop (Tauri) estão registrados como backlog para uma fase futura e não fazem parte desta iteração.

### Pré-requisitos

- **Docker** e **Docker Compose** instalados
- **Python 3.11+** com as dependências de desenvolvimento instaladas
- **Playwright Chromium** instalado

### 1. Instalar dependências Python

```bash
cd backend
pip install -r requirements-dev.txt
```

### 2. Instalar o navegador Playwright

```bash
playwright install chromium
```

### 3. Subir o ambiente E2E

O ambiente E2E usa uma instância separada do banco de dados (PostgreSQL na porta 5456) e da aplicação (porta 8001), completamente isolada do ambiente de desenvolvimento.

```bash
docker-compose -f docker-compose.e2e.yml up -d
```

Aguarde o serviço ficar saudável (cerca de 30 segundos):

```bash
docker-compose -f docker-compose.e2e.yml ps
```

### 4. Executar o seed de dados

Insere a API key de teste no banco de dados E2E:

```bash
cd backend
python -m tests.e2e.seed
```

### 5. Executar os testes E2E

```bash
cd backend
pytest -m e2e -v
```

### 6. Encerrar o ambiente E2E

```bash
docker-compose -f docker-compose.e2e.yml down -v
```

### Configurações de qualidade

| Parâmetro | Valor | Critério |
|-----------|-------|----------|
| Timeout total | 900s (15 min) | Suíte completa < 15 min |
| Reruns por falha | 2 tentativas | Flakiness < 2% |
| Delay entre reruns | 2s | Estabilidade |

### Portas do ambiente E2E

| Serviço | Porta E2E | Porta Dev |
|---------|-----------|-----------|
| Aplicação | 8001 | 8000 |
| PostgreSQL | 5456 | 5455 |
| Redis | 6383 | 6382 |

### Estrutura dos testes E2E

```
backend/tests/e2e/
├── __init__.py
├── conftest.py          # Fixtures compartilhadas (banco, browser, API client)
├── seed.py              # Script de seed de dados para o banco E2E
└── test_*.py            # Arquivos de teste E2E
```
