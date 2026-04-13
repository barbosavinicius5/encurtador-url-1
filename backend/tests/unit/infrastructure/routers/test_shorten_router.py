"""Testes unitários para o shorten_router."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import create_app
from app.domain.entities.api_key import ApiKey
from app.domain.entities.shortened_url import ShortenedUrl
from app.application.dtos.shorten_url_dto import ShortenUrlResponse
from app.application.use_cases.shorten_url_use_case import ShortenUrlUseCase
from app.api.dependencies.api_key_auth import api_key_auth
from tests.helpers import MockUrlRepository, MockSettings


@pytest.fixture
def valid_api_key():
    return ApiKey(key="test-api-key-12345678", owner="test-owner")


@pytest.fixture
def mock_repo():
    return MockUrlRepository()


@pytest.fixture
def app_instance():
    return create_app()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shorten_url_sucesso(app_instance, mock_repo, valid_api_key):
    """POST /api/shorten com URL válida e API key válida retorna 201."""
    settings = MockSettings()

    mock_use_case = AsyncMock(spec=ShortenUrlUseCase)
    mock_use_case.execute.return_value = ShortenUrlResponse(
        short_code="abc123",
        short_url="http://localhost:8000/abc123",
        original_url="https://www.exemplo.com/pagina-longa",
    )

    app_instance.dependency_overrides[api_key_auth] = lambda: valid_api_key

    with patch(
        "app.infrastructure.di.container.get_shorten_use_case",
        new=AsyncMock(return_value=mock_use_case),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_instance), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/shorten",
                json={"url": "https://www.exemplo.com/pagina-longa"},
                headers={"X-API-Key": "test-api-key-12345678"},
            )

    app_instance.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert "short_code" in body
    assert "short_url" in body
    assert "original_url" in body


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shorten_url_sem_api_key_retorna_401(app_instance):
    """POST /api/shorten sem X-API-Key retorna 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app_instance), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/shorten",
            json={"url": "https://www.exemplo.com/pagina-longa"},
        )

    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shorten_url_com_url_invalida_retorna_422(app_instance, valid_api_key):
    """POST /api/shorten com URL inválida retorna 422."""
    from app.application.use_cases.shorten_url_use_case import ShortenUrlUseCase

    mock_use_case = AsyncMock(spec=ShortenUrlUseCase)
    mock_use_case.execute.side_effect = ValueError("URL inválida")

    app_instance.dependency_overrides[api_key_auth] = lambda: valid_api_key

    with patch(
        "app.infrastructure.di.container.get_shorten_use_case",
        new=AsyncMock(return_value=mock_use_case),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_instance), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/shorten",
                json={"url": "nao-e-uma-url-valida"},
                headers={"X-API-Key": "test-api-key-12345678"},
            )

    app_instance.dependency_overrides.clear()

    assert response.status_code == 422
