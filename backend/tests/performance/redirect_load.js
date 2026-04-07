/**
 * Teste de Carga — Redirecionamento (GET /{short_code})
 *
 * Objetivo: Validar que p95 de latência é ≤ 100ms sob 50 usuários virtuais simultâneos.
 *
 * Pré-requisitos:
 *   - k6 instalado: https://k6.io/docs/get-started/installation/
 *   - Aplicação rodando com curto short_code pré-aquecido no cache Redis
 *
 * Uso:
 *   BASE_URL=http://localhost:8000 SHORT_CODE=aB12x k6 run redirect_load.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const redirectDuration = new Trend('redirect_duration', true);
const errorRate = new Rate('error_rate');

export const options = {
  vus: 50,            // 50 usuários virtuais simultâneos
  duration: '30s',    // duração do teste
  thresholds: {
    'redirect_duration': ['p(95)<100'],  // p95 ≤ 100ms (SLA da US-002)
    'http_req_failed': ['rate<0.01'],    // < 1% de erros HTTP
    'error_rate': ['rate<0.01'],         // < 1% de respostas inesperadas
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const SHORT_CODE = __ENV.SHORT_CODE || 'aB12x';  // short_code válido pré-cadastrado e aquecido no cache

export default function () {
  const res = http.get(`${BASE_URL}/${SHORT_CODE}`, {
    redirects: 0,  // não seguir o redirect — medir apenas tempo de resposta do serviço
  });

  redirectDuration.add(res.timings.duration);

  const isValidStatus = res.status === 301 || res.status === 302;
  errorRate.add(!isValidStatus);

  check(res, {
    'status é 301 ou 302': (r) => r.status === 301 || r.status === 302,
    'latência < 100ms': (r) => r.timings.duration < 100,
    'header Location presente': (r) => r.headers['Location'] !== undefined,
  });

  sleep(0.1);  // pausa de 100ms entre iterações por VU
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  const { metrics } = data;
  const p50 = metrics.redirect_duration?.values?.['p(50)'] ?? 'N/A';
  const p95 = metrics.redirect_duration?.values?.['p(95)'] ?? 'N/A';
  const p99 = metrics.redirect_duration?.values?.['p(99)'] ?? 'N/A';
  const errorRateVal = metrics.error_rate?.values?.rate ?? 0;
  const totalRequests = metrics.http_reqs?.values?.count ?? 0;
  const rps = metrics.http_reqs?.values?.rate ?? 0;

  return `
=== Resumo do Teste de Carga — Redirecionamento ===
  p50:              ${typeof p50 === 'number' ? p50.toFixed(2) : p50} ms
  p95:              ${typeof p95 === 'number' ? p95.toFixed(2) : p95} ms ${typeof p95 === 'number' && p95 <= 100 ? '✅' : '❌'}
  p99:              ${typeof p99 === 'number' ? p99.toFixed(2) : p99} ms
  Taxa de erros:    ${(errorRateVal * 100).toFixed(2)}%
  Total requisições: ${totalRequests}
  RPS médio:        ${typeof rps === 'number' ? rps.toFixed(2) : rps}
`;
}
