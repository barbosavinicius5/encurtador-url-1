"""Testes unitários para o redirect_router."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.main import create_app
from app.application.use_cases.redirect_url_use_case import RedirectUrlUseCase
from app.infrastructure.di.container import get_redirect_use_case


@pytest.fixture
def app_instance():
    return create_app()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redirect_sucesso_retorna_302(app_instance):
    """GET /{short_code} com código válido retorna 302 redirect."""
    mock_use_case = AsyncMock(spec=RedirectUrlUseCase)
    mock_use_case.execute.return_value = "https://www.exemplo.com/pagina-original"

    # O redirect_router usa Depends(get_redirect_use_case) e o FastAPI
    # resolve via dependency_overrides em runtime
    app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

    async with AsyncClient(
        transport=ASGITransport(app=app_instance),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        response = await client.get("/abc123")

    app_instance.dependency_overrides.clear()

    assert response.status_code == 302
    assert "https://www.exemplo.com/pagina-original" in response.headers["location"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redirect_codigo_inexistente_retorna_404(app_instance):
    """GET /{short_code} com código inexistente retorna 404 HTML."""
    mock_use_case = AsyncMock(spec=RedirectUrlUseCase)
    mock_use_case.execute.side_effect = ValueError("short_code não encontrado")

    app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

    async with AsyncClient(
        transport=ASGITransport(app=app_instance),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        response = await client.get("/codigo-inexistente")

    app_instance.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_retorna_200(app_instance):
    """GET /health retorna 200 com status ok."""
    async with AsyncClient(
        transport=ASGITransport(app=app_instance),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
