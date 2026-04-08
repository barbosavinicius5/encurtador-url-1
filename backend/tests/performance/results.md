# Resultados do Teste de Carga — Redirecionamento (GET /{short_code})

## Cenário

- **Endpoint:** `GET /{short_code}` (redirect HTTP 302)
- **Usuários virtuais:** 50 simultâneos (workers do vegeta)
- **Taxa de requisições:** 50 RPS (requests per second) sustentados
- **Duração:** 30 segundos
- **Total de requisições:** 1.500
- **URLs testadas:** 10 short_codes distintos (`perf01` a `perf10`), distribuídos ciclicamente
- **Ferramenta:** [Vegeta](https://github.com/tsenart/vegeta) v12.11.1
- **Estratégia de cache:** short_codes pré-aquecidos no Redis (100% cache hit)

## Configuração do Ambiente

| Item | Detalhe |
|------|---------|
| Hardware | Intel Core i7-11800H @ 2.30GHz, 16 vCPUs, 31 GB RAM |
| OS | Linux (Ubuntu 22.04) |
| Python | 3.12.0 |
| FastAPI | 0.115.x |
| Uvicorn | single worker (desenvolvimento) |
| Redis | 7.4.7 (Docker) |
| PostgreSQL | 15.17 (Docker) |
| SQLAlchemy | 2.0.45 (pool_size=20, max_overflow=30) |
| `CACHE_TTL_SECONDS` | 3600 (default) |
| `ENVIRONMENT` | staging |

## Resultados Principais

| Percentil | Latência (ms) | SLA |
|-----------|--------------|-----|
| p50       | 4.3 ms       | — |
| p90       | 4.9 ms       | — |
| **p95**   | **5.2 ms**   | **≤ 100ms ✅** |
| p99       | 5.9 ms       | — |
| p99.9     | 6.6 ms       | — |
| máximo    | 6.6 ms       | — |

## Métricas de Throughput

| Métrica | Valor |
|---------|-------|
| Total de requisições | 1.500 |
| Taxa efetiva (RPS) | 50.03 |
| Taxa de erros HTTP | 0.00% |
| Tempo total de teste | 29.98 s |

## Critério SLA (US-002)

> **p95 ≤ 100ms**: **APROVADO ✅**

O p95 medido foi de **5.2ms**, confirmando que 95% das requisições são atendidas em menos de 6ms
— significativamente abaixo do SLA de 100ms especificado na US-002.

## Observações Técnicas

1. **Cache aquecido:** todas as requisições resultaram em cache hit no Redis, retornando a URL
   sem consultar o banco de dados. Isso confirma o comportamento esperado para tráfego de pico.

2. **Click count fire-and-forget:** o incremento de cliques é processado em background via
   `asyncio.create_task()` usando uma sessão de banco de dados independente (corrigido nesta task
   para evitar contention de sessão com a requisição HTTP principal).

3. **Isolamento de sessão para tasks de background:** o `RedirectUrlUseCase` recebe um
   `session_factory` via DI para criar sessões frescas nos background tasks de click_count,
   eliminando o erro de `IllegalStateChangeError` que ocorria quando a sessão do request
   HTTP era encerrada antes da task concluir.

4. **TTL configurável:** o parâmetro `CACHE_TTL_SECONDS=3600` foi usado neste teste.
   O mesmo comportamento de latência é esperado para outros valores de TTL, pois o TTL
   afeta apenas a duração da entrada no cache, não a latência de leitura.

## Reprodução do Teste

```bash
# Pré-requisitos: Docker, vegeta, Python 3.12+

# 1. Iniciar infraestrutura
docker-compose up -d postgres redis

# 2. Criar URLs de teste no banco
python3 -c "..."  # script em tests/performance/setup_test_data.py

# 3. Aquecer o cache Redis
python3 -c "..."  # (ver locustfile.py para detalhes)

# 4. Iniciar a aplicação
CACHE_TTL_SECONDS=3600 ENVIRONMENT=staging uvicorn app.main:app --port 8001

# 5. Executar o teste de carga
vegeta attack \
  -targets=tests/performance/vegeta_targets.txt \
  -rate=50 \
  -duration=30s \
  -max-connections=50 \
  -redirects=-1 | vegeta report
```

## Arquivo de Alvos (vegeta_targets.txt)

O arquivo `tests/performance/vegeta_targets.txt` contém os 10 short_codes de teste:

```
GET http://localhost:8001/perf01
GET http://localhost:8001/perf02
...
GET http://localhost:8001/perf10
```

## Script k6 Equivalente

Ver `tests/performance/redirect_load.js` para a versão k6 do teste de carga,
que pode ser executada com:

```bash
BASE_URL=http://localhost:8001 SHORT_CODE=perf01 k6 run tests/performance/redirect_load.js
```
