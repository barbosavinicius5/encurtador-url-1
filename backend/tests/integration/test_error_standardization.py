"""Testes de integração para padronização de erros e ErrorResponse.

Cenários BDD para a T002-BE:
- Erros de validação retornam ErrorResponse padronizado (422)
- Recurso não encontrado retorna ErrorResponse padronizado (404)
- Autenticação ausente retorna ErrorResponse padronizado (401)
- Rate limit excedido retorna ErrorResponse padronizado (429)
- Erro interno não expõe stack trace (500)
- Redirect de browser mantém comportamento HTML
- Endpoints de sucesso não são afetados
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.api_key_auth import api_key_auth, get_api_key_repository
from app.application.use_cases.get_url_details_use_case import UrlNotFoundError
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


class TestErrorResponseSchema:
    """Testes unitários para o schema ErrorResponse."""

    def test_error_response_schema_importavel(self):
        """ErrorResponse deve ser importável de app.application.dtos.error_response."""
        from app.application.dtos.error_response import ErrorResponse

        assert ErrorResponse is not None

    def test_error_response_campos_obrigatorios(self):
        """ErrorResponse deve ter campos status_code, error_type e message."""
        from app.application.dtos.error_response import ErrorResponse

        error = ErrorResponse(
            status_code=404,
            error_type="NOT_FOUND",
            message="URL encurtada não encontrada.",
        )
        assert error.status_code == 404
        assert error.error_type == "NOT_FOUND"
        assert error.message == "URL encurtada não encontrada."

    def test_error_response_serializa_para_dict(self):
        """ErrorResponse.model_dump() deve retornar dict com campos corretos."""
        from app.application.dtos.error_response import ErrorResponse

        error = ErrorResponse(
            status_code=401,
            error_type="UNAUTHORIZED",
            message="API key ausente ou inválida.",
        )
        data = error.model_dump()
        assert data == {
            "status_code": 401,
            "error_type": "UNAUTHORIZED",
            "message": "API key ausente ou inválida.",
        }


class TestValidationErrorHandler:
    """Cenário A: Erro de validação retorna ErrorResponse padronizado (422)."""

    @pytest.mark.asyncio
    async def test_post_sem_campo_url_retorna_422_com_error_response(self, app, client):
        """POST /api/v1/shorten sem campo url retorna 422 com ErrorResponse."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        try:
            response = await client.post(
                "/api/v1/shorten",
                json={},
                headers={"X-API-Key": "valid-key"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        assert "status_code" in data
        assert "error_type" in data
        assert "message" in data
        assert data["status_code"] == 422
        assert data["error_type"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_post_url_invalida_retorna_422_com_error_response(self, app, client):
        """POST /api/v1/shorten com URL inválida retorna 422 com ErrorResponse."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        try:
            response = await client.post(
                "/api/v1/shorten",
                json={"url": "nao-e-url-valida"},
                headers={"X-API-Key": "valid-key"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422
        data = response.json()
        assert data["error_type"] == "VALIDATION_ERROR"
        assert data["status_code"] == 422
        assert len(data["message"]) > 0

    @pytest.mark.asyncio
    async def test_422_response_nao_tem_campo_detail(self, app, client):
        """ErrorResponse de validação NÃO deve ter campo 'detail' (formato antigo)."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        try:
            response = await client.post(
                "/api/v1/shorten",
                json={},
                headers={"X-API-Key": "valid-key"},
            )
        finally:
            app.dependency_overrides.clear()

        data = response.json()
        # Novo formato não deve ter 'detail' no nível raiz
        assert "detail" not in data


class TestNotFoundErrorHandler:
    """Cenário B: Recurso não encontrado retorna ErrorResponse padronizado (404)."""

    @pytest.mark.asyncio
    async def test_get_url_inexistente_retorna_404_com_error_response(self, app, client):
        """GET /api/v1/urls/inexistente retorna 404 com ErrorResponse."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()

        async def mock_use_case_raises(*args, **kwargs):
            raise UrlNotFoundError("inexistente")

        with patch("app.infrastructure.di.container.get_url_details_use_case") as mock_dep:
            mock_uc = AsyncMock()
            mock_uc.execute = AsyncMock(side_effect=UrlNotFoundError("inexistente"))
            mock_dep.return_value = mock_uc

            try:
                response = await client.get(
                    "/api/v1/urls/inexistente",
                    headers={"X-API-Key": "valid-key"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        assert data["status_code"] == 404
        assert data["error_type"] == "NOT_FOUND"
        assert "message" in data
        assert len(data["message"]) > 0
        # Não deve ter 'detail' no nível raiz
        assert "detail" not in data


class TestUnauthorizedErrorHandler:
    """Cenário C: Autenticação ausente retorna ErrorResponse padronizado (401)."""

    @pytest.mark.asyncio
    async def test_sem_api_key_retorna_401_com_error_response(self, client):
        """Requisição sem API key retorna 401 com ErrorResponse."""
        response = await client.post(
            "/api/v1/shorten",
            json={"url": "https://exemplo.com"},
        )

        assert response.status_code == 401
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        assert data["status_code"] == 401
        assert data["error_type"] == "UNAUTHORIZED"
        assert "message" in data
        # Não deve ter 'detail' no nível raiz
        assert "detail" not in data

    @pytest.mark.asyncio
    async def test_api_key_invalida_retorna_401_com_error_response(self, app, client):
        """Requisição com API key inválida retorna 401 com ErrorResponse."""
        mock_repo = AsyncMock()
        mock_repo.get_by_key.return_value = None
        app.dependency_overrides[get_api_key_repository] = lambda: mock_repo

        try:
            response = await client.post(
                "/api/v1/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "chave-invalida"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 401
        data = response.json()
        assert data["status_code"] == 401
        assert data["error_type"] == "UNAUTHORIZED"
        assert "detail" not in data


class TestRateLimitErrorHandler:
    """Cenário D: Rate limit excedido retorna ErrorResponse padronizado (429)."""

    @pytest.mark.asyncio
    async def test_rate_limit_excedido_retorna_429_com_error_response(self, app, client):
        """Rate limit excedido retorna 429 com ErrorResponse."""
        valid_key = _make_valid_api_key()
        mock_repo = AsyncMock()
        mock_repo.get_by_key.return_value = valid_key

        async def mock_rate_limit_exceeded(api_key_value: str, settings):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=429,
                detail={
                    "error_type": "RATE_LIMIT_EXCEEDED",
                    "message": "Limite de requisições excedido. Tente novamente mais tarde.",
                },
                headers={"Retry-After": "60"},
            )

        app.dependency_overrides[get_api_key_repository] = lambda: mock_repo
        with patch(
            "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
            side_effect=mock_rate_limit_exceeded,
        ):
            try:
                response = await client.post(
                    "/api/v1/shorten",
                    json={"url": "https://exemplo.com"},
                    headers={"X-API-Key": "valid-api-key-abc123"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 429
        assert response.headers["content-type"].startswith("application/json")
        assert "Retry-After" in response.headers

        data = response.json()
        assert data["status_code"] == 429
        assert data["error_type"] == "RATE_LIMIT_EXCEEDED"
        assert "message" in data
        assert "detail" not in data


class TestInternalErrorHandler:
    """Cenário E: Erro interno não expõe stack trace (500)."""

    @pytest.mark.asyncio
    async def test_excecao_interna_retorna_500_sem_stack_trace(self, app, client):
        """Exceção não tratada retorna 500 com ErrorResponse sem stack trace."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()

        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_uc = AsyncMock()
            mock_uc.execute = AsyncMock(
                side_effect=RuntimeError("Erro interno simulado para teste")
            )
            mock_dep.return_value = mock_uc

            try:
                response = await client.post(
                    "/api/v1/shorten",
                    json={"url": "https://exemplo.com"},
                    headers={"X-API-Key": "valid-key"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 500
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        assert data["status_code"] == 500
        assert data["error_type"] == "INTERNAL_ERROR"
        assert "message" in data

        # Stack trace NÃO deve aparecer no body
        response_text = response.text
        assert "Traceback" not in response_text
        assert "RuntimeError" not in response_text
        assert "simulado" not in response_text  # Não expõe mensagem interna
        assert "detail" not in data


class TestRedirectBrowserBehavior:
    """Cenário F: Redirect de browser mantém comportamento HTML."""

    @pytest.mark.asyncio
    async def test_slug_inexistente_com_accept_html_retorna_html(self, app, client):
        """GET /slug_inexistente com Accept: text/html retorna HTML 404."""
        from app.infrastructure.di.container import get_redirect_use_case
        from app.infrastructure.middleware.brute_force_protection import brute_force_protection
        from app.infrastructure.middleware.rate_limiter import rate_limit_by_ip

        async def _no_rate_limit():
            pass

        async def _no_brute_force():
            pass

        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(side_effect=ValueError("not found"))

        app.dependency_overrides[rate_limit_by_ip] = _no_rate_limit
        app.dependency_overrides[brute_force_protection] = _no_brute_force
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_uc

        try:
            response = await client.get(
                "/slug-inexistente-xyz",
                headers={"Accept": "text/html,application/xhtml+xml"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type

    @pytest.mark.asyncio
    async def test_slug_existente_retorna_redirect(self, app, client):
        """GET /slug_existente retorna 302 redirect."""
        from app.infrastructure.di.container import get_redirect_use_case
        from app.infrastructure.middleware.brute_force_protection import brute_force_protection
        from app.infrastructure.middleware.rate_limiter import rate_limit_by_ip

        async def _no_rate_limit():
            pass

        async def _no_brute_force():
            pass

        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(return_value="https://www.exemplo.com")

        app.dependency_overrides[rate_limit_by_ip] = _no_rate_limit
        app.dependency_overrides[brute_force_protection] = _no_brute_force
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_uc

        try:
            response = await client.get(
                "/slug-existente",
                follow_redirects=False,
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 302
        assert response.headers["location"] == "https://www.exemplo.com"


class TestSuccessNotAffected:
    """Cenário G: Endpoints de sucesso não são afetados pelos handlers."""

    @pytest.mark.asyncio
    async def test_post_valido_retorna_201_com_dados_corretos(self, app, client):
        """POST /api/v1/shorten válido retorna 201 (não ErrorResponse)."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()

        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_uc = AsyncMock()
            mock_uc.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="aB3kZ9",
                    short_url="https://short.app/aB3kZ9",
                    original_url="https://exemplo.com/pagina-longa",
                )
            )
            mock_dep.return_value = mock_uc

            try:
                response = await client.post(
                    "/api/v1/shorten",
                    json={"url": "https://exemplo.com/pagina-longa"},
                    headers={"X-API-Key": "valid-key"},
                )
            finally:
                app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        # Resposta de sucesso NÃO deve ter campos de ErrorResponse
        assert "error_type" not in data
        assert "short_code" in data
        assert "short_url" in data


class TestOpenAPIDocumentation:
    """Cenário H: Documentação OpenAPI acessível e com exemplos de erro."""

    @pytest.mark.asyncio
    async def test_docs_acessivel(self, client):
        """GET /docs deve retornar 200."""
        response = await client.get("/docs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc_acessivel(self, client):
        """GET /redoc deve retornar 200."""
        response = await client.get("/redoc")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_json_valido(self, client):
        """GET /openapi.json deve retornar JSON válido com ErrorResponse em schemas."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "components" in schema
        assert "schemas" in schema["components"]
        assert "ErrorResponse" in schema["components"]["schemas"]

    @pytest.mark.asyncio
    async def test_openapi_shorten_tem_responses_de_erro(self, client):
        """POST /api/v1/shorten deve ter responses 401, 422, 429, 500 no OpenAPI."""
        response = await client.get("/openapi.json")
        schema = response.json()

        paths = schema.get("paths", {})
        shorten_path = paths.get("/api/v1/shorten", {})
        post_op = shorten_path.get("post", {})
        responses = post_op.get("responses", {})

        assert "401" in responses
        assert "422" in responses
        assert "429" in responses
        assert "500" in responses

    @pytest.mark.asyncio
    async def test_openapi_url_details_tem_responses_de_erro(self, client):
        """GET /api/v1/urls/{short_code} deve ter responses 401, 404, 429, 500 no OpenAPI."""
        response = await client.get("/openapi.json")
        schema = response.json()

        paths = schema.get("paths", {})
        url_details_path = paths.get("/api/v1/urls/{short_code}", {})
        get_op = url_details_path.get("get", {})
        responses = get_op.get("responses", {})

        assert "401" in responses
        assert "404" in responses
        assert "429" in responses
        assert "500" in responses
