# Spike Técnico: Abordagem para Testes do Servidor MCP

**Data:** 2026-04-13  
**Autor:** FactorCode (Agent)  
**Prazo do Spike:** 3 dias úteis  
**Status:** Concluído

---

## Contexto

O projeto encurtador de URL utiliza agentes de IA que se comunicam com serviços externos via Model Context Protocol (MCP). Para garantir testes determinísticos sem consumo de créditos reais de API, é necessário definir uma estratégia para testar o servidor MCP de forma controlada.

Este documento analisa 3 abordagens candidatas, apresenta critérios de decisão e recomenda a abordagem mais adequada para o projeto.

---

## Opções Analisadas

### Opção 1: Mock Transport via `httpx.MockTransport`

**Descrição:** Substituir o transport HTTP do cliente MCP por um `MockTransport` que intercepta todas as requisições e retorna payloads pré-definidos sem fazer conexões reais.

**Implementação:**
```python
import httpx

class MCPMockTransport(httpx.MockTransport):
    def handle_request(self, request):
        # Roteamento baseado na URL da requisição
        if "/mcp/tools/generate_short_code" in str(request.url):
            return httpx.Response(200, json={"result": "aB12x"})
        return httpx.Response(404, json={"error": "Tool not found"})

# No conftest de integração:
@pytest.fixture
def mock_mcp_client():
    transport = MCPMockTransport()
    return httpx.AsyncClient(transport=transport, base_url="http://mcp-server")
```

**Vantagens:**
- Simples de implementar — sem dependências extras
- Controle total sobre payloads de resposta
- Integração direta com fixtures existentes
- Sem necessidade de servidor real

**Desvantagens:**
- Não valida o protocolo MCP — apenas simula HTTP
- Mudanças na API MCP podem não ser detectadas
- Requer manutenção manual dos payloads mockados

**Complexidade:** Baixa  
**Cobertura de contrato:** Baixa (apenas HTTP, não MCP)

---

### Opção 2: Servidor MCP em Processo com `pytest-asyncio`

**Descrição:** Iniciar um servidor MCP real (ou stub) dentro do processo de teste, usando `asyncio` para gerenciar o ciclo de vida. O servidor responde a requisições MCP reais mas com dados de teste.

**Implementação:**
```python
import asyncio
import pytest_asyncio
from mcp.server import MCPServer  # hipotético

@pytest_asyncio.fixture(scope="session")
async def mcp_test_server():
    server = MCPServer(host="127.0.0.1", port=0)  # porta aleatória
    
    @server.tool("generate_short_code")
    async def generate_short_code(url: str) -> str:
        return "aB12x"  # resposta determinística
    
    await server.start()
    yield server
    await server.stop()
```

**Vantagens:**
- Valida o protocolo MCP real (handshake, serialização, etc.)
- Detecta mudanças de contrato entre cliente e servidor
- Respostas determinísticas mas com protocolo real

**Desvantagens:**
- Requer biblioteca MCP SDK instalada (`mcp`)
- Complexidade maior de setup
- Pode ter dependências de porta e rede (mesmo que loopback)
- Mais lento que mock puro

**Complexidade:** Média  
**Cobertura de contrato:** Alta (protocolo MCP completo)

---

### Opção 3: `respx` com Padrões de URL MCP

**Descrição:** Usar `respx` (já definido como dependência) para interceptar requisições HTTP ao servidor MCP no nível da camada de transporte, com padrões de URL correspondentes às rotas MCP esperadas.

**Implementação:**
```python
import respx
import httpx
import pytest

@pytest.fixture
def mock_mcp_server():
    with respx.mock(base_url="http://mcp-server") as mock:
        # Tool: generate_short_code
        mock.post("/mcp/tools/generate_short_code").mock(
            return_value=httpx.Response(200, json={
                "content": [{"type": "text", "text": "aB12x"}]
            })
        )
        
        # Tool: analyze_url
        mock.post("/mcp/tools/analyze_url").mock(
            return_value=httpx.Response(200, json={
                "content": [{"type": "text", "text": '{"category": "e-commerce", "safe": true}'}]
            })
        )
        
        yield mock
```

**Vantagens:**
- Consistente com a fixture `block_external_http` já definida (usa `respx`)
- Sem dependências extras além do `respx`
- Controle granular por rota MCP
- Integração natural com fixtures existentes do conftest

**Desvantagens:**
- Não valida protocolo MCP nativo — simula apenas HTTP
- Acoplado à implementação de URL das rotas MCP

**Complexidade:** Baixa-Média  
**Cobertura de contrato:** Média (HTTP, padrões de URL, payloads)

---

## Matriz de Critérios

| Critério | Peso | Opção 1 (MockTransport) | Opção 2 (Servidor Real) | Opção 3 (respx) |
|----------|------|------------------------|------------------------|-----------------|
| Facilidade de implementação | 30% | ★★★★★ (5) | ★★★ (3) | ★★★★ (4) |
| Cobertura de contrato MCP | 25% | ★★ (2) | ★★★★★ (5) | ★★★ (3) |
| Consistência com infra existente | 20% | ★★★ (3) | ★★ (2) | ★★★★★ (5) |
| Performance no CI | 15% | ★★★★★ (5) | ★★★ (3) | ★★★★★ (5) |
| Manutenibilidade | 10% | ★★★ (3) | ★★★★ (4) | ★★★★ (4) |
| **Score ponderado** | | **3.65** | **3.60** | **4.15** |

---

## Recomendação

**Opção 3: `respx` com padrões de URL MCP**

### Justificativa

A Opção 3 apresenta o melhor score ponderado (4.15) e é consistente com a estratégia de interceptação HTTP já definida no `conftest.py` de integração (fixture `block_external_http` usa `respx`). Isso evita a introdução de um novo padrão de mock na suite.

A Opção 2 (servidor real) seria ideal para cobertura máxima de contrato, mas o overhead de implementação e a dependência da biblioteca `mcp` não justificam o ganho neste momento — especialmente considerando que a suite deve completar em menos de 5 minutos no CI.

A Opção 1 (MockTransport direto) é tecnicamente equivalente mas menos idiomática no contexto do projeto, onde `respx` já é a ferramenta padrão.

### Ressalvas

- Se o projeto evoluir para um servidor MCP com protocolo não-HTTP (ex: stdio ou WebSocket), a Opção 3 precisará ser revisada e a Opção 2 se tornará mais atrativa.
- A cobertura de contrato da Opção 3 não detecta mudanças no schema de serialização MCP — é recomendável adicionar testes contract-level com Pact ou similar em uma US futura.

---

## Próximos Passos

1. **Instalar `respx`** como dependência de desenvolvimento: `pip install respx>=0.20`
2. **Adicionar `respx` ao `requirements-dev.txt`**
3. **Criar fixture `mock_mcp_server`** no `tests/integration/conftest.py` seguindo o padrão da Opção 3
4. **Documentar rotas MCP esperadas** em um arquivo de contrato (`docs/mcp-contract.md`) para facilitar manutenção dos mocks
5. **Revisar** esta decisão quando o servidor MCP estiver implementado e as rotas reais forem conhecidas

---

## Referências

- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification)
- [respx Documentation](https://lundberg.github.io/respx/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- Fixture `block_external_http` em `tests/integration/conftest.py`
