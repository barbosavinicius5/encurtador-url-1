"""Middleware de captura de métricas de latência e contadores via Prometheus."""

import time

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Histograma de latência das requisições HTTP
# Buckets padrão do Prometheus são adequados para APIs web
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Latência das requisições HTTP em segundos",
    ["method", "route"],
)

# Contador de requisições HTTP por método, rota e status code
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total de requisições HTTP",
    ["method", "route", "status_code"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware que captura métricas de latência e contadores de requisições.

    Registra no Prometheus:
    - Duração de cada requisição via histograma (por método e rota)
    - Total de requisições via contador (por método, rota e status code)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Captura tempo de início e fim da requisição para calcular latência.

        Args:
            request: Requisição HTTP recebida.
            call_next: Próximo middleware ou handler na cadeia.

        Returns:
            Resposta com métricas registradas no Prometheus.
        """
        start_time = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start_time
        route = request.url.path
        method = request.method
        status_code = str(response.status_code)

        REQUEST_LATENCY.labels(method=method, route=route).observe(duration)
        REQUEST_COUNT.labels(method=method, route=route, status_code=status_code).inc()

        return response
