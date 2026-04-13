"""Testes unitários para o url_details_router."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import create_app
from app.domain.entities.api_key import ApiKey
from app.application.use_cases.get_url_details_use_case import (
    GetUrlDetailsUseCase,
    UrlNotFoundError,
)
from app.application.dtos.get_url_details_dto import GetUrlDetailsResponse
from app.api.dependencies.api_key_auth import api_key_auth


@pytest.fixture
def valid_api_key():
    return ApiKey(key="test-api-key-12345678", owner="test-owner")


@pytest.fixture
def app_instance():
    return create_app()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_url_details_sucesso_retorna_200(app_instance, valid_api_key):
    """GET /api/urls/{short_code} com código válido retorna 200 com detalhes."""
    mock_use_case = AsyncMock(spec=GetUrlDetailsUseCase)
    mock_use_case.execute.return_value = GetUrlDetailsResponse(
        original_url="https://www.exemplo.com/pagina-original",
        short_code="abc123",
        short_url="https://short.app/abc123",
        click_count=42,
    )

    app_instance.dependency_overrides[api_key_auth] = lambda: valid_api_key

    with patch(
        "app.infrastructure.di.container.get_url_details_use_case",
        new=AsyncMock(return_value=mock_use_case),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/urls/abc123",
                headers={"X-API-Key": "test-api-key-12345678"},
            )

    app_instance.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["original_url"] == "https://www.exemplo.com/pagina-original"
    assert body["short_code"] == "abc123"
    assert body["click_count"] == 42


@pytest.mark.unit
@pytest.mark.asyncio
async def test_url_details_codigo_inexistente_retorna_404(app_instance, valid_api_key):
    """GET /api/urls/{short_code} com código inexistente retorna 404."""
    mock_use_case = AsyncMock(spec=GetUrlDetailsUseCase)
    mock_use_case.execute.side_effect = UrlNotFoundError("codigo-inexistente")

    app_instance.dependency_overrides[api_key_auth] = lambda: valid_api_key

    with patch(
        "app.infrastructure.di.container.get_url_details_use_case",
        new=AsyncMock(return_value=mock_use_case),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/urls/codigo-inexistente",
                headers={"X-API-Key": "test-api-key-12345678"},
            )

    app_instance.dependency_overrides.clear()

    assert response.status_code == 404
    body = response.json()
    assert "detail" in body


@pytest.mark.unit
@pytest.mark.asyncio
async def test_url_details_click_count_zero(app_instance, valid_api_key):
    """GET /api/urls/{short_code} com 0 cliques retorna click_count=0."""
    mock_use_case = AsyncMock(spec=GetUrlDetailsUseCase)
    mock_use_case.execute.return_value = GetUrlDetailsResponse(
        original_url="https://www.exemplo.com/nova-pagina",
        short_code="xyz789",
        short_url="https://short.app/xyz789",
        click_count=0,
    )

    app_instance.dependency_overrides[api_key_auth] = lambda: valid_api_key

    with patch(
        "app.infrastructure.di.container.get_url_details_use_case",
        new=AsyncMock(return_value=mock_use_case),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/urls/xyz789",
                headers={"X-API-Key": "test-api-key-12345678"},
            )

    app_instance.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["click_count"] == 0
