"""Testes de integração para autenticação por API Key no endpoint POST /api/shorten."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.api_key_auth import api_key_auth, get_api_key_repository
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
    """Cria uma ApiKey válida para uso nos testes."""
    return ApiKey(id="test-id", key="valid-api-key-abc123", owner="test-owner", is_active=True)


def _make_mock_shorten_use_case():
    """Cria um mock do ShortenUrlUseCase."""
    mock_use_case = AsyncMock()
    mock_use_case.execute = AsyncMock(
        return_value=MagicMock(
            short_code="aB3kZ9",
            short_url="https://short.app/aB3kZ9",
            original_url="https://exemplo.com/pagina-longa",
        )
    )
    return mock_use_case


class TestApiKeyAuth:
    """Testes para autenticação por API Key no endpoint de encurtamento."""

    @pytest.mark.asyncio
    async def test_sem_api_key_retorna_401(self, client):
        """POST /api/shorten sem X-API-Key deve retornar 401."""
        response = await client.post(
            "/api/shorten",
            json={"url": "https://exemplo.com/pagina"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "inválida" in data["detail"].lower() or "inativa" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_api_key_invalida_retorna_401(self, app, client):
        """POST /api/shorten com X-API-Key inválida deve retornar 401."""
        mock_repo = AsyncMock()
        mock_repo.get_by_key.return_value = None
        app.dependency_overrides[get_api_key_repository] = lambda: mock_repo
        try:
            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com/pagina"},
                headers={"X-API-Key": "chave-invalida-xyz"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_api_key_inativa_retorna_401(self, app, client):
        """POST /api/shorten com X-API-Key inativa deve retornar 401."""
        inactive_key = ApiKey(
            id="test-id",
            key="inactive-key",
            owner="test-owner",
            is_active=False,
        )
        mock_repo = AsyncMock()
        mock_repo.get_by_key.return_value = inactive_key
        app.dependency_overrides[get_api_key_repository] = lambda: mock_repo
        try:
            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com/pagina"},
                headers={"X-API-Key": "inactive-key"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_valida_retorna_201(self, app, client):
        """POST /api/shorten com X-API-Key válida deve retornar 201."""
        valid_key = _make_valid_api_key()

        # Override completo do api_key_auth para evitar DB e Redis
        app.dependency_overrides[api_key_auth] = lambda: valid_key

        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_dep.return_value = _make_mock_shorten_use_case()
            try:
                response = await client.post(
                    "/api/shorten",
                    json={"url": "https://exemplo.com/pagina"},
                    headers={"X-API-Key": "valid-api-key-abc123"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert "short_url" in data
        assert "short_code" in data

    @pytest.mark.asyncio
    async def test_rate_limit_excedido_retorna_429(self, app, client):
        """POST /api/shorten com rate limit excedido deve retornar 429 com Retry-After."""
        valid_key = _make_valid_api_key()
        mock_repo = AsyncMock()
        mock_repo.get_by_key.return_value = valid_key

        async def mock_rate_limit_exceeded(api_key_value: str, settings):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=429,
                detail="Rate limit excedido. Tente novamente em 60 segundos.",
                headers={"Retry-After": "60"},
            )

        app.dependency_overrides[get_api_key_repository] = lambda: mock_repo
        with patch(
            "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
            side_effect=mock_rate_limit_exceeded,
        ):
            try:
                response = await client.post(
                    "/api/shorten",
                    json={"url": "https://exemplo.com/pagina"},
                    headers={"X-API-Key": "valid-api-key-abc123"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        data = response.json()
        assert "detail" in data
        assert "rate limit" in data["detail"].lower() or "limit" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_rate_limit_contagem_por_api_key_nao_por_ip(self, app, client):
        """Rate limit deve ser por API Key — chaves diferentes não se bloqueiam entre si."""
        valid_key_a = ApiKey(id="id-a", key="key-a-unique", owner="owner-a", is_active=True)
        valid_key_b = ApiKey(id="id-b", key="key-b-unique", owner="owner-b", is_active=True)

        from fastapi import HTTPException

        async def rate_limit_side_effect(api_key_value: str, settings):
            if api_key_value == "key-a-unique":
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit excedido. Tente novamente em 60 segundos.",
                    headers={"Retry-After": "60"},
                )

        def get_key_by_value(key_val: str) -> ApiKey | None:
            if key_val == "key-a-unique":
                return valid_key_a
            if key_val == "key-b-unique":
                return valid_key_b
            return None

        mock_repo = AsyncMock()
        mock_repo.get_by_key = AsyncMock(side_effect=lambda k: get_key_by_value(k))

        app.dependency_overrides[get_api_key_repository] = lambda: mock_repo

        with (
            patch(
                "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
                side_effect=rate_limit_side_effect,
            ),
            patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep,
        ):
            mock_dep.return_value = _make_mock_shorten_use_case()
            try:
                response_a = await client.post(
                    "/api/shorten",
                    json={"url": "https://exemplo.com"},
                    headers={"X-API-Key": "key-a-unique"},
                )

                response_b = await client.post(
                    "/api/shorten",
                    json={"url": "https://exemplo.com"},
                    headers={"X-API-Key": "key-b-unique"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response_a.status_code == 429
        assert response_b.status_code == 201
