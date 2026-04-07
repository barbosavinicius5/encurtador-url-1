"""Testes de integração para o endpoint GET /{short_code} (US-002)."""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.di.container import get_redirect_use_case
from app.infrastructure.middleware.brute_force_protection import brute_force_protection
from app.infrastructure.middleware.rate_limiter import rate_limit_by_ip
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _apply_rate_limit_bypass(app):
    """Aplica mocks de bypass das dependencies de rate limiting para testes de redirect."""

    async def _no_rate_limit():
        pass

    async def _no_brute_force():
        pass

    app.dependency_overrides[rate_limit_by_ip] = _no_rate_limit
    app.dependency_overrides[brute_force_protection] = _no_brute_force


class TestRedirectEndpoint:
    """Testes de integração para o endpoint de redirect."""

    @pytest.mark.asyncio
    async def test_redirect_slug_valido_retorna_302(self, app, client):
        """Slug válido deve retornar HTTP 302."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(return_value="https://example.com")

        _apply_rate_limit_bypass(app)
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case
        try:
            response = await client.get("/abc123", follow_redirects=False)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_redirect_slug_valido_header_location_correto(self, app, client):
        """Slug válido deve retornar Location com URL original."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(return_value="https://example.com")

        _apply_rate_limit_bypass(app)
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case
        try:
            response = await client.get("/abc123", follow_redirects=False)
        finally:
            app.dependency_overrides.clear()

        assert response.headers["location"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_redirect_nao_usa_301(self, app, client):
        """Redirect deve usar 302 (não 301) para não ser cacheado pelo browser."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(return_value="https://example.com")

        _apply_rate_limit_bypass(app)
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case
        try:
            response = await client.get("/abc123", follow_redirects=False)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 302
        assert response.status_code != 301

    @pytest.mark.asyncio
    async def test_redirect_slug_invalido_retorna_404(self, app, client):
        """Slug inválido deve retornar HTTP 404."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(
            side_effect=ValueError("short_code 'invalido' não encontrado")
        )

        _apply_rate_limit_bypass(app)
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case
        try:
            response = await client.get("/invalido", follow_redirects=False)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_redirect_slug_invalido_retorna_html(self, app, client):
        """Slug inválido deve retornar Content-Type text/html."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(
            side_effect=ValueError("short_code 'invalido' não encontrado")
        )

        _apply_rate_limit_bypass(app)
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case
        try:
            response = await client.get("/invalido", follow_redirects=False)
        finally:
            app.dependency_overrides.clear()

        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_redirect_slug_invalido_html_contem_mensagem_erro(self, app, client):
        """Slug inválido deve retornar HTML com mensagem amigável."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(
            side_effect=ValueError("short_code 'invalido' não encontrado")
        )

        _apply_rate_limit_bypass(app)
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case
        try:
            response = await client.get("/invalido", follow_redirects=False)
        finally:
            app.dependency_overrides.clear()

        assert "não encontrado" in response.text.lower() or "não existe" in response.text.lower()

    @pytest.mark.asyncio
    async def test_redirect_slug_invalido_nao_retorna_json(self, app, client):
        """Slug inválido não deve retornar JSON."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(
            side_effect=ValueError("short_code 'invalido' não encontrado")
        )

        _apply_rate_limit_bypass(app)
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case
        try:
            response = await client.get("/invalido", follow_redirects=False)
        finally:
            app.dependency_overrides.clear()

        # Não deve ter application/json no content-type
        assert "application/json" not in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_redirect_html_404_contem_doctype(self, app, client):
        """Página de erro deve ser um HTML válido com DOCTYPE."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(side_effect=ValueError("não encontrado"))

        _apply_rate_limit_bypass(app)
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case
        try:
            response = await client.get("/invalido", follow_redirects=False)
        finally:
            app.dependency_overrides.clear()

        assert "<!DOCTYPE html>" in response.text or "<!doctype html>" in response.text.lower()

    @pytest.mark.asyncio
    async def test_redirect_html_404_contem_link_para_home(self, app, client):
        """Página de erro deve conter link para a página inicial."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(side_effect=ValueError("não encontrado"))

        _apply_rate_limit_bypass(app)
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case
        try:
            response = await client.get("/invalido", follow_redirects=False)
        finally:
            app.dependency_overrides.clear()

        assert 'href="/"' in response.text

    @pytest.mark.asyncio
    async def test_redirect_html_404_tem_viewport_meta(self, app, client):
        """Página de erro deve ter viewport meta tag para responsividade."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(side_effect=ValueError("não encontrado"))

        _apply_rate_limit_bypass(app)
        app.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case
        try:
            response = await client.get("/invalido", follow_redirects=False)
        finally:
            app.dependency_overrides.clear()

        assert 'name="viewport"' in response.text


class TestHealthEndpoint:
    """Testes para o endpoint GET /health."""

    @pytest.mark.asyncio
    async def test_health_retorna_200(self, client):
        """GET /health deve retornar HTTP 200."""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_retorna_json_status_ok(self, client):
        """GET /health deve retornar JSON com status ok."""
        response = await client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_nao_exige_autenticacao(self, client):
        """GET /health deve ser acessível sem autenticação."""
        response = await client.get("/health")
        assert response.status_code != 401
        assert response.status_code != 403
