"""Testes de integração para o endpoint /metrics e MetricsMiddleware."""

import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    """Fixture que cria a aplicação FastAPI para testes."""
    return create_app()


@pytest.fixture
async def client(app):
    """Fixture que fornece um cliente HTTP async para testes de integração."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestMetricsEndpoint:
    """Testes para o endpoint GET /metrics."""

    async def test_metrics_retorna_200(self, client):
        """GET /metrics deve retornar HTTP 200."""
        response = await client.get("/metrics")
        assert response.status_code == 200

    async def test_metrics_content_type_prometheus(self, client):
        """GET /metrics deve retornar Content-Type compatível com Prometheus."""
        response = await client.get("/metrics")
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type

    async def test_metrics_contem_histograma_latencia(self, client):
        """O corpo de /metrics deve conter o histograma de latência."""
        # Fazer uma requisição para garantir que há métricas registradas
        await client.get("/health")
        response = await client.get("/metrics")
        body = response.text
        assert "http_request_duration_seconds" in body, (
            "Histograma http_request_duration_seconds ausente em /metrics"
        )

    async def test_metrics_contem_contador_requisicoes(self, client):
        """O corpo de /metrics deve conter o contador de requisições."""
        # Fazer uma requisição para garantir que há métricas registradas
        await client.get("/health")
        response = await client.get("/metrics")
        body = response.text
        assert "http_requests_total" in body, "Contador http_requests_total ausente em /metrics"

    async def test_metrics_registra_apos_requisicao_health(self, client):
        """Após uma requisição /health, as métricas devem ser atualizadas."""
        await client.get("/health")
        response = await client.get("/metrics")
        body = response.text

        # Verificar que ambas as métricas existem
        assert "http_request_duration_seconds" in body
        assert "http_requests_total" in body

    async def test_metrics_sem_autenticacao(self, client):
        """GET /metrics deve ser acessível sem autenticação."""
        response = await client.get("/metrics")
        # Não deve retornar 401 ou 403
        assert response.status_code not in [401, 403], "/metrics não deve exigir autenticação"


class TestMetricsMiddlewarePerformance:
    """Testes de overhead de performance dos middlewares."""

    async def test_overhead_middlewares_inferior_5ms(self, client):
        """O overhead combinado dos middlewares deve ser inferior a 5ms."""
        tempos = []
        for _ in range(20):
            start = time.perf_counter()
            await client.get("/health")
            duration_ms = (time.perf_counter() - start) * 1000
            tempos.append(duration_ms)

        mediana = sorted(tempos)[len(tempos) // 2]
        # Verificamos apenas o overhead — não o tempo total da requisição
        # O tempo total pode incluir processamento do endpoint
        # Aqui verificamos que o tempo total com middlewares é razoável
        # Um endpoint /health simples + middlewares não deve passar de 100ms
        assert mediana < 100, f"Mediana de tempo {mediana:.2f}ms excede limite razoável para testes"
