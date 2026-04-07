"""Testes de integração para o endpoint GET /api/v1/urls/{short_code}."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.api_key_auth import api_key_auth, get_api_key_repository
from app.application.dtos.get_url_details_dto import GetUrlDetailsResponse
from app.application.use_cases.get_url_details_use_case import (
    GetUrlDetailsUseCase,
    UrlNotFoundError,
)
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


class TestUrlDetailsEndpoint:
    """Testes para o endpoint GET /api/v1/urls/{short_code}."""

    @pytest.mark.asyncio
    async def test_get_url_existente_retorna_200(self, app, client):
        """GET /api/v1/urls/{short_code} com URL existente deve retornar 200."""
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
                    headers={"X-API-Key": "valid-api-key-abc123"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["original_url"] == "https://www.exemplo.com/pagina"
        assert data["short_code"] == "abc123"
        assert data["short_url"] == "https://short.app/abc123"
        assert data["click_count"] == 5

    @pytest.mark.asyncio
    async def test_get_url_inexistente_retorna_404(self, app, client):
        """GET /api/v1/urls/{short_code} com short_code inexistente deve retornar 404."""
        valid_key = _make_valid_api_key()
        mock_use_case = AsyncMock(spec=GetUrlDetailsUseCase)
        mock_use_case.execute.side_effect = UrlNotFoundError("inexistente")

        app.dependency_overrides[api_key_auth] = lambda: valid_key

        with patch("app.infrastructure.di.container.get_url_details_use_case") as mock_dep:
            mock_dep.return_value = mock_use_case
            try:
                response = await client.get(
                    "/api/v1/urls/inexistente",
                    headers={"X-API-Key": "valid-api-key-abc123"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "não encontrada" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_url_sem_api_key_retorna_401(self, client):
        """GET /api/v1/urls/{short_code} sem X-API-Key deve retornar 401."""
        response = await client.get("/api/v1/urls/abc123")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_url_com_api_key_invalida_retorna_401(self, app, client):
        """GET /api/v1/urls/{short_code} com API key inválida deve retornar 401."""
        mock_repo = AsyncMock()
        mock_repo.get_by_key.return_value = None

        app.dependency_overrides[get_api_key_repository] = lambda: mock_repo
        try:
            response = await client.get(
                "/api/v1/urls/abc123",
                headers={"X-API-Key": "chave-invalida"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_response_contem_todos_os_campos(self, app, client):
        """Resposta deve conter todos os campos esperados."""
        valid_key = _make_valid_api_key()
        expected_response = GetUrlDetailsResponse(
            original_url="https://exemplo.com",
            short_code="test01",
            short_url="https://short.app/test01",
            click_count=0,
        )
        mock_use_case = AsyncMock(spec=GetUrlDetailsUseCase)
        mock_use_case.execute.return_value = expected_response

        app.dependency_overrides[api_key_auth] = lambda: valid_key

        with patch("app.infrastructure.di.container.get_url_details_use_case") as mock_dep:
            mock_dep.return_value = mock_use_case
            try:
                response = await client.get(
                    "/api/v1/urls/test01",
                    headers={"X-API-Key": "valid-api-key-abc123"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "original_url" in data
        assert "short_code" in data
        assert "short_url" in data
        assert "click_count" in data

    @pytest.mark.asyncio
    async def test_click_count_reflete_valor_atual(self, app, client):
        """click_count deve refletir o valor atual no banco."""
        valid_key = _make_valid_api_key()
        expected_response = GetUrlDetailsResponse(
            original_url="https://exemplo.com",
            short_code="test01",
            short_url="https://short.app/test01",
            click_count=42,
        )
        mock_use_case = AsyncMock(spec=GetUrlDetailsUseCase)
        mock_use_case.execute.return_value = expected_response

        app.dependency_overrides[api_key_auth] = lambda: valid_key

        with patch("app.infrastructure.di.container.get_url_details_use_case") as mock_dep:
            mock_dep.return_value = mock_use_case
            try:
                response = await client.get(
                    "/api/v1/urls/test01",
                    headers={"X-API-Key": "valid-api-key-abc123"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["click_count"] == 42


class TestSwaggerDocumentation:
    """Testes para verificar que a documentação Swagger está acessível."""

    @pytest.mark.asyncio
    async def test_swagger_ui_acessivel(self, client):
        """GET /docs deve retornar 200 com interface Swagger."""
        response = await client.get("/docs")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc_acessivel(self, client):
        """GET /redoc deve retornar 200 com interface ReDoc."""
        response = await client.get("/redoc")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_json_contem_endpoint_shorten(self, client):
        """OpenAPI JSON deve conter o endpoint /api/v1/shorten."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "/api/v1/shorten" in data["paths"]

    @pytest.mark.asyncio
    async def test_openapi_json_contem_endpoint_url_details(self, client):
        """OpenAPI JSON deve conter o endpoint /api/v1/urls/{short_code}."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "/api/v1/urls/{short_code}" in data["paths"]
