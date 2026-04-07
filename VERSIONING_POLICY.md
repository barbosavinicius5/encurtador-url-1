# Política de Versionamento da API

## Versão atual: v1

## Paths

- Todos os endpoints REST públicos estão sob `/api/v1/`.
- O endpoint de redirect de browser (`/{short_code}`) e `/health` estão fora do versionamento.
- O endpoint `/metrics` está fora do versionamento (infraestrutura interna).

## Endpoints Versionados

| Método | Path v1 | Descrição |
|--------|---------|-----------|
| POST | `/api/v1/shorten` | Encurtar uma URL |
| GET | `/api/v1/links` | Listar links da sessão |
| GET | `/api/v1/urls/{short_code}` | Consultar detalhes de uma URL encurtada |

## Endpoints Fora do Versionamento

| Método | Path | Motivo |
|--------|------|--------|
| GET | `/{short_code}` | Redirect de browser — não é API REST |
| GET | `/health` | Health check de infraestrutura |
| GET | `/metrics` | Métricas Prometheus — uso interno |

## Quando uma nova versão (v2, v3...) é necessária

Uma nova versão de API é necessária quando há **breaking change**, ou seja:

- Remoção de campo obrigatório do request ou response.
- Mudança de tipo de um campo existente (ex.: string → number).
- Remoção de endpoint existente.
- Mudança de semântica de um endpoint (mesmo path, comportamento diferente).
- Alteração do nome de um campo existente no request ou response.
- Mudança no código HTTP de resposta para uma situação já mapeada.

## O que NÃO exige nova versão

- Adição de novo campo **opcional** no response (retrocompatível).
- Adição de novo endpoint.
- Correção de bug que alinha o comportamento com a documentação existente.
- Mudanças internas de implementação sem impacto no contrato público.
- Melhorias de performance sem alteração de contrato.
- Atualização de dependências internas sem impacto no contrato.

## Compatibilidade retroativa

Os paths legados emitem redirect HTTP 301 (Moved Permanently) para os paths versionados correspondentes:

| Método | Path legado | Path novo (destino do 301) |
|--------|-------------|---------------------------|
| POST | `/api/shorten` | `/api/v1/shorten` |
| GET | `/api/links` | `/api/v1/links` |
| GET | `/api/urls/{short_code}` | `/api/v1/urls/{short_code}` |

Clientes devem atualizar suas integrações para usar os paths `/api/v1/` diretamente.
Os redirects 301 serão mantidos por pelo menos 6 meses após o lançamento de uma nova versão.

## Comunicação de mudanças

Qualquer breaking change que exija nova versão de API deve ser:

1. Documentada neste arquivo com antecedência mínima de 30 dias.
2. Comunicada a todos os consumidores conhecidos da API via canais oficiais.
3. Implementada com período de coexistência entre versões (mínimo 90 dias).
