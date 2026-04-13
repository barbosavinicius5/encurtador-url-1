"""Testes unitários para o links_router."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch
from datetime import UTC, datetime

from app.main import create_app
from app.application.use_cases.list_links_use_case import ListLinksUseCase
from app.domain.entities.shortened_url import ShortenedUrl


@pytest.fixture
def app_instance():
    return create_app()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_links_com_sessao_retorna_200(app_instance):
    """GET /api/links com session_id cookie retorna 200 com lista de links."""
    now = datetime.now(UTC)
    mock_use_case = AsyncMock(spec=ListLinksUseCase)
    mock_use_case.execute.return_value = [
        ShortenedUrl(
            id=1,
            original_url="https://www.exemplo.com/pagina-longa",
            short_code="abc123",
            click_count=5,
            created_at=now,
            session_id="test-session-id",
        )
    ]

    with patch(
        "app.infrastructure.di.container.get_list_links_use_case",
        new=AsyncMock(return_value=mock_use_case),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/links",
                cookies={"session_id": "test-session-id"},
            )

    assert response.status_code == 200
    body = response.json()
    assert "links" in body
    assert len(body["links"]) == 1
    assert body["links"][0]["short_code"] == "abc123"
    assert body["links"][0]["click_count"] == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_links_sem_sessao_retorna_lista_vazia(app_instance):
    """GET /api/links sem session_id retorna 200 com lista vazia."""
    mock_use_case = AsyncMock(spec=ListLinksUseCase)
    mock_use_case.execute.return_value = []

    with patch(
        "app.infrastructure.di.container.get_list_links_use_case",
        new=AsyncMock(return_value=mock_use_case),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/links")

    assert response.status_code == 200
    body = response.json()
    assert "links" in body
    assert body["links"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_links_repositorio_vazio_retorna_lista_vazia(app_instance):
    """GET /api/links com sessão existente mas sem links retorna lista vazia."""
    mock_use_case = AsyncMock(spec=ListLinksUseCase)
    mock_use_case.execute.return_value = []

    with patch(
        "app.infrastructure.di.container.get_list_links_use_case",
        new=AsyncMock(return_value=mock_use_case),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/links",
                cookies={"session_id": "sessao-sem-links"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["links"] == []
