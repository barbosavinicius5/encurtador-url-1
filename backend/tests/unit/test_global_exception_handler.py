"""Testes unitários para o handler global de exceções e sanitização de erros."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def client_no_raise(app):
    """Cliente que não re-lança exceções do servidor — permite testar handlers globais."""
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        yield ac


class TestGlobalExceptionHandler:
    """Testes para o handler global de exceções."""

    @pytest.mark.asyncio
    async def test_handler_global_captura_runtime_error_retorna_500(self, app, client):
        """Cenário A: RuntimeError não tratada deve retornar HTTP 500 sem stack trace."""
        from app.api.dependencies.api_key_auth import api_key_auth
        from app.domain.entities.api_key import ApiKey

        app.dependency_overrides[api_key_auth] = lambda: ApiKey(
            id="test-id", key="valid-key", owner="test", is_active=True
        )

        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(side_effect=RuntimeError("Erro interno secreto"))
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com/pagina"},
                headers={"X-API-Key": "valid-key"},
            )

        app.dependency_overrides.clear()

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        # Não deve expor stack trace ou mensagem interna
        assert "Erro interno secreto" not in data["detail"]
        assert "RuntimeError" not in data["detail"]
        # Deve ter mensagem amigável
        assert data["detail"] == "Ocorreu um erro inesperado. Tente novamente mais tarde."

    @pytest.mark.asyncio
    async def test_handler_global_captura_exception_generica_retorna_500(
        self, app, client_no_raise
    ):
        """Cenário B: Exception genérica não tratada deve retornar HTTP 500 sem detalhes internos.

        Quando uma exceção genérica (não HTTPException, ValueError ou RuntimeError) sobe do
        use case sem ser capturada pelo router, o handler global deve interceptar e retornar
        a mensagem padronizada sem expor detalhes internos.
        Usa client_no_raise para que o handler global possa retornar a JSONResponse ao cliente.
        """
        from app.api.dependencies.api_key_auth import api_key_auth
        from app.domain.entities.api_key import ApiKey

        app.dependency_overrides[api_key_auth] = lambda: ApiKey(
            id="test-id", key="valid-key", owner="test", is_active=True
        )

        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            # Simula uma AttributeError (não capturada pelo except do router)
            mock_use_case.execute = AsyncMock(
                side_effect=AttributeError("Detalhe técnico: conexão recusada porta 5432")
            )
            mock_dep.return_value = mock_use_case

            response = await client_no_raise.post(
                "/api/shorten",
                json={"url": "https://exemplo.com/pagina"},
                headers={"X-API-Key": "valid-key"},
            )

        app.dependency_overrides.clear()

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "5432" not in data["detail"]
        assert "conexão recusada" not in data["detail"]
        assert data["detail"] == "Ocorreu um erro inesperado. Tente novamente mais tarde."

    @pytest.mark.asyncio
    async def test_erro_validacao_pydantic_nao_interceptado_pelo_handler_global(self, app, client):
        """Cenário F: Erros de validação Pydantic devem continuar retornando 422."""
        from app.api.dependencies.api_key_auth import api_key_auth
        from app.domain.entities.api_key import ApiKey

        app.dependency_overrides[api_key_auth] = lambda: ApiKey(
            id="test-id", key="valid-key", owner="test", is_active=True
        )

        # Envia payload inválido (sem campo 'url')
        response = await client.post(
            "/api/shorten",
            json={"campo_invalido": "valor"},
            headers={"X-API-Key": "valid-key"},
        )

        app.dependency_overrides.clear()

        assert response.status_code == 422
        data = response.json()
        # Formato padrão do FastAPI para erros de validação
        assert "detail" in data
        # Não deve ser a mensagem do handler global
        assert data["detail"] != "Ocorreu um erro inesperado. Tente novamente mais tarde."

    @pytest.mark.asyncio
    async def test_erro_404_via_redirect_router_nao_retorna_500(self, app, client_no_raise):
        """Handler global não deve interceptar 404s retornados via ValueError no redirect router.

        O redirect_router captura ValueError em seu try/except e retorna HTMLResponse 404.
        Para testar isso corretamente, mockamos o use_case.execute para lançar ValueError.
        """
        from app.infrastructure.routers.redirect_router import get_redirect_use_case

        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(side_effect=ValueError("Slug não encontrado"))
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

        response = await client_no_raise.get("/slug-inexistente")

        app.dependency_overrides.clear()

        # O redirect_router trata ValueError como 404, não 500
        assert response.status_code == 404
        # Não deve ser a resposta JSON do handler global de 500
        content_type = response.headers.get("content-type", "")
        assert "application/json" not in content_type or response.json().get("detail") != (
            "Ocorreu um erro inesperado. Tente novamente mais tarde."
        )

    @pytest.mark.asyncio
    async def test_sanitizacao_shorten_router_nao_expoe_detalhes_internos(self, app, client):
        """Cenário G: O router sanitizado não deve expor str(e) em erros 500."""
        from app.api.dependencies.api_key_auth import api_key_auth
        from app.domain.entities.api_key import ApiKey

        app.dependency_overrides[api_key_auth] = lambda: ApiKey(
            id="test-id", key="valid-key", owner="test", is_active=True
        )

        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            # Simula RuntimeError que seria capturado pelo bloco except do router
            mock_use_case.execute = AsyncMock(
                side_effect=RuntimeError("senha_secreta_banco: postgres123")
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com/pagina"},
                headers={"X-API-Key": "valid-key"},
            )

        app.dependency_overrides.clear()

        assert response.status_code == 500
        data = response.json()
        assert "postgres123" not in data.get("detail", "")
        assert "senha_secreta" not in data.get("detail", "")
        assert data["detail"] == "Ocorreu um erro inesperado. Tente novamente mais tarde."
