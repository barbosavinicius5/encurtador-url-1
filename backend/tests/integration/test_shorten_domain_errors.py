"""Testes de integração para mapeamento de exceptions de domínio no endpoint de encurtamento v1."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.api_key_auth import api_key_auth
from app.domain.entities.api_key import ApiKey
from app.domain.exceptions import InvalidUrlError, MaliciousDomainError, SlugCollisionError
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _make_valid_api_key() -> ApiKey:
    return ApiKey(id="test-id", key="valid-key", owner="test", is_active=True)


class TestShortenEndpointDomainErrors:
    """Testes de integração para mapeamento de exceptions de domínio."""

    @pytest.mark.asyncio
    async def test_url_invalida_retorna_422(self, app, client):
        """POST /api/v1/shorten com URL inválida deve retornar 422."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                side_effect=InvalidUrlError(
                    url="nao-e-uma-url", reason="scheme '' não permitido; use http ou https"
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/v1/shorten",
                json={"url": "nao-e-uma-url"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        data = response.json()
        # Novo formato ErrorResponse (T002-BE)
        assert data["error_type"] == "VALIDATION_ERROR"
        assert data["status_code"] == 422

    @pytest.mark.asyncio
    async def test_dominio_malicioso_retorna_422_com_mensagem(self, app, client):
        """POST /api/v1/shorten com domínio bloqueado deve retornar 422 com mensagem descritiva."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                side_effect=MaliciousDomainError(domain="phishing.com")
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/v1/shorten",
                json={"url": "https://phishing.com/login"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        data = response.json()
        # Novo formato ErrorResponse (T002-BE)
        assert data["error_type"] == "VALIDATION_ERROR"
        assert "bloqueado" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_slug_colisao_retorna_409(self, app, client):
        """POST /api/v1/shorten com slug em colisão deve retornar 409."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(side_effect=SlugCollisionError(slug="abc123"))
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/v1/shorten",
                json={"url": "https://valido.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 409
        data = response.json()
        # Novo formato ErrorResponse (T002-BE)
        assert data["error_type"] == "CONFLICT"
        assert data["status_code"] == 409

    @pytest.mark.asyncio
    async def test_url_valida_retorna_201(self, app, client):
        """POST /api/v1/shorten com URL válida deve retornar 201."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="abc123",
                    short_url="https://short.app/abc123",
                    original_url="https://valido.com",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/v1/shorten",
                json={"url": "https://valido.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert "original_url" in data
