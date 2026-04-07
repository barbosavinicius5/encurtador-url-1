"""Testes de integração para versionamento de rotas e compatibilidade retroativa.

Valida que:
- Endpoints versionados /api/v1/... funcionam corretamente
- Rotas legadas /api/... emitem redirect HTTP 301
- Endpoints fora do versionamento (/{short_code}, /health) não são afetados
- Documentação OpenAPI reflete paths versionados
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.api_key_auth import api_key_auth
from app.domain.entities.api_key import ApiKey
from app.infrastructure.middleware.brute_force_protection import brute_force_protection
from app.infrastructure.middleware.rate_limiter import rate_limit_by_ip
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        yield ac


def _make_valid_api_key() -> ApiKey:
    return ApiKey(id="test-id", key="valid-key", owner="test", is_active=True)


class TestVersionedEndpoints:
    """Testa que os endpoints versionados /api/v1/... funcionam corretamente."""

    @pytest.mark.asyncio
    async def test_post_api_v1_shorten_retorna_201(self, app, client):
        """POST /api/v1/shorten deve retornar 201 com payload válido."""
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
                "/api/v1/shorten",
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
    async def test_get_api_v1_links_retorna_200(self, client):
        """GET /api/v1/links deve retornar 200."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            response = await client.get("/api/v1/links")

        assert response.status_code == 200
        data = response.json()
        assert data == {"links": []}

    @pytest.mark.asyncio
    async def test_get_api_v1_urls_short_code_retorna_200(self, app, client):
        """GET /api/v1/urls/{short_code} deve retornar 200 com URL existente."""
        from app.application.dtos.get_url_details_dto import GetUrlDetailsResponse
        from app.application.use_cases.get_url_details_use_case import GetUrlDetailsUseCase

        valid_key = _make_valid_api_key()
        expected_response = GetUrlDetailsResponse(
            original_url="https://www.exemplo.com/pagina",
            short_code="abc123",
            short_url="https://short.app/abc123",
            click_count=5,
        )
        mock_use_case = AsyncMock(spec=GetUrlDetailsUseCase)
        mock_use_case.execute.return_value = expected_response

        app.dependency_overrides[api_key_auth] = lambda: valid_key

        with patch("app.infrastructure.di.container.get_url_details_use_case") as mock_dep:
            mock_dep.return_value = mock_use_case
            try:
                response = await client.get(
                    "/api/v1/urls/abc123",
                    headers={"X-API-Key": "valid-key"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == "abc123"


class TestLegacyRedirects:
    """Testa que rotas legadas /api/... emitem redirect HTTP 301."""

    @pytest.mark.asyncio
    async def test_post_api_shorten_retorna_301(self, client):
        """POST /api/shorten deve retornar HTTP 301 (sem seguir redirect)."""
        response = await client.post(
            "/api/shorten",
            json={"url": "https://exemplo.com"},
            headers={"X-API-Key": "valid-key"},
        )

        assert response.status_code == 301
        assert response.headers.get("location") == "/api/v1/shorten"

    @pytest.mark.asyncio
    async def test_get_api_links_retorna_301(self, client):
        """GET /api/links deve retornar HTTP 301."""
        response = await client.get("/api/links")

        assert response.status_code == 301
        assert response.headers.get("location") == "/api/v1/links"

    @pytest.mark.asyncio
    async def test_get_api_urls_short_code_retorna_301(self, client):
        """GET /api/urls/{short_code} deve retornar HTTP 301 preservando short_code."""
        response = await client.get("/api/urls/aB12x")

        assert response.status_code == 301
        assert response.headers.get("location") == "/api/v1/urls/aB12x"

    @pytest.mark.asyncio
    async def test_get_api_links_retorna_301_com_location_correto(self, client):
        """Header Location deve apontar para /api/v1/links exatamente."""
        response = await client.get("/api/links")

        assert response.status_code == 301
        location = response.headers.get("location")
        assert location is not None
        assert location == "/api/v1/links"

    @pytest.mark.asyncio
    async def test_get_api_urls_preserva_short_code_no_redirect(self, client):
        """Redirect de /api/urls/{short_code} deve preservar o short_code no Location."""
        short_code = "xYz789"
        response = await client.get(f"/api/urls/{short_code}")

        assert response.status_code == 301
        location = response.headers.get("location")
        assert location == f"/api/v1/urls/{short_code}"


class TestNonVersionedEndpoints:
    """Testa que endpoints fora do versionamento não são afetados."""

    @pytest.mark.asyncio
    async def test_health_retorna_200(self, client):
        """GET /health deve retornar 200 sem alterações."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

    @pytest.mark.asyncio
    async def test_redirect_short_code_nao_e_afetado(self, app, client):
        """GET /{short_code} deve ser processado pelo redirect_router sem interferência."""

        # Bypass dos middlewares de rate limiting e brute force (requerem Redis)
        async def _no_rate_limit():
            pass

        async def _no_brute_force():
            pass

        app.dependency_overrides[rate_limit_by_ip] = _no_rate_limit
        app.dependency_overrides[brute_force_protection] = _no_brute_force

        from app.infrastructure.di.container import get_redirect_use_case

        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(return_value="https://exemplo.com/pagina-longa")
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

        try:
            response = await client.get("/aB12x")
        finally:
            app.dependency_overrides.clear()

        # Deve ser HTTP 302 (redirect do browser), não 301 de compatibilidade retroativa
        assert response.status_code == 302
        assert response.headers.get("location") == "https://exemplo.com/pagina-longa"


class TestOpenAPIDocumentation:
    """Testa que a documentação OpenAPI reflete paths versionados."""

    @pytest.mark.asyncio
    async def test_openapi_json_contem_paths_versionados(self, client):
        """OpenAPI JSON deve conter os paths /api/v1/..."""
        async with AsyncClient(
            transport=ASGITransport(app=(await _get_app())),
            base_url="http://test",
        ) as ac:
            response = await ac.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        paths = data.get("paths", {})

        assert "/api/v1/shorten" in paths
        assert "/api/v1/links" in paths
        assert "/api/v1/urls/{short_code}" in paths

    @pytest.mark.asyncio
    async def test_openapi_json_nao_contem_paths_legados(self, client):
        """OpenAPI JSON não deve conter paths legados (include_in_schema=False)."""
        async with AsyncClient(
            transport=ASGITransport(app=(await _get_app())),
            base_url="http://test",
        ) as ac:
            response = await ac.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        paths = data.get("paths", {})

        assert "/api/shorten" not in paths
        assert "/api/links" not in paths
        assert "/api/urls/{short_code}" not in paths

    @pytest.mark.asyncio
    async def test_openapi_title_reflete_versao_v1(self, client):
        """OpenAPI info.title deve indicar versão v1."""
        async with AsyncClient(
            transport=ASGITransport(app=(await _get_app())),
            base_url="http://test",
        ) as ac:
            response = await ac.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        info = data.get("info", {})
        assert "v1" in info.get("title", "").lower() or "1.0" in info.get("version", "")

    @pytest.mark.asyncio
    async def test_docs_acessivel(self, client):
        """GET /docs deve estar acessível."""
        response = await client.get("/docs")
        assert response.status_code == 200


async def _get_app():
    """Cria uma nova instância da app para testes de documentação."""
    return create_app()
