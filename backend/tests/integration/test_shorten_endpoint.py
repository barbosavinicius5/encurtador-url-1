"""Testes de integração para o endpoint POST /api/shorten."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.api_key_auth import api_key_auth
from app.domain.entities.api_key import ApiKey
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


class TestShortenEndpoint:
    """Testes de integração para o endpoint de encurtamento."""

    @pytest.mark.asyncio
    async def test_post_url_valida_retorna_201(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="aB3kZ9",
                    short_url="https://short.app/aB3kZ9",
                    original_url="https://exemplo.com/pagina-longa",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com/pagina-longa"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert "original_url" in data

    @pytest.mark.asyncio
    async def test_post_url_invalida_retorna_422(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "nao-e-uma-url"},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_url_vazia_retorna_422(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": ""},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_sem_protocolo_retorna_422(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "exemplo.com/pagina"},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_short_code_tem_minimo_5_chars(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="abc12",
                    short_url="https://short.app/abc12",
                    original_url="https://exemplo.com",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert len(data["short_code"]) >= 5

    @pytest.mark.asyncio
    async def test_response_short_url_comeca_com_https(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="abc12",
                    short_url="https://short.app/abc12",
                    original_url="https://exemplo.com",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["short_url"].startswith("https://")
