"""Testes de integração para RequestIdMiddleware."""

import uuid

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


class TestRequestIdMiddleware:
    """Testes para o middleware que gera e propaga request_id."""

    async def test_resposta_contem_header_x_request_id(self, client):
        """Cada resposta deve conter o header X-Request-ID."""
        response = await client.get("/health")
        assert "x-request-id" in response.headers, "Header X-Request-ID ausente na resposta"

    async def test_x_request_id_eh_uuid_v4_valido(self, client):
        """O valor do header X-Request-ID deve ser um UUID v4 válido."""
        response = await client.get("/health")
        request_id = response.headers.get("x-request-id")
        assert request_id is not None

        # Valida formato UUID v4
        try:
            parsed_uuid = uuid.UUID(request_id, version=4)
            assert str(parsed_uuid) == request_id
        except ValueError:
            pytest.fail(f"X-Request-ID '{request_id}' não é um UUID v4 válido")

    async def test_cada_requisicao_tem_request_id_unico(self, client):
        """Requisições diferentes devem ter request_ids diferentes."""
        response1 = await client.get("/health")
        response2 = await client.get("/health")

        id1 = response1.headers.get("x-request-id")
        id2 = response2.headers.get("x-request-id")

        assert id1 != id2, "Duas requisições distintas devem ter request_ids diferentes"

    async def test_request_id_presente_em_endpoint_metrics(self, client):
        """O header X-Request-ID deve estar presente em qualquer endpoint."""
        response = await client.get("/metrics")
        assert "x-request-id" in response.headers

    async def test_x_request_id_nao_vazio(self, client):
        """O header X-Request-ID não deve ser vazio."""
        response = await client.get("/health")
        request_id = response.headers.get("x-request-id", "")
        assert len(request_id) > 0, "X-Request-ID não pode ser vazio"
