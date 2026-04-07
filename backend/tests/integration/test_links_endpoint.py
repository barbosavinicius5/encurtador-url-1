"""Testes de integração para o endpoint GET /api/v1/links e cookie de sessão."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.api_key_auth import api_key_auth
from app.domain.entities.api_key import ApiKey
from app.domain.entities.shortened_url import ShortenedUrl
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


def make_entity(short_code: str, session_id: str, click_count: int = 0) -> ShortenedUrl:
    """Helper para criar entidades de teste."""
    return ShortenedUrl(
        original_url=f"https://example.com/{short_code}",
        short_code=short_code,
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        click_count=click_count,
        session_id=session_id,
    )


class TestListLinksEndpoint:
    """Testes de integração para o endpoint GET /api/links."""

    @pytest.mark.asyncio
    async def test_sem_cookie_retorna_lista_vazia(self, client):
        """GET /api/v1/links sem cookie deve retornar 200 com lista vazia."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            response = await client.get("/api/v1/links")

        assert response.status_code == 200
        data = response.json()
        assert data == {"links": []}

    @pytest.mark.asyncio
    async def test_com_cookie_e_links_retorna_lista(self, client):
        """GET /api/v1/links com cookie e links deve retornar a lista."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        link1 = make_entity("abc123", session_id, click_count=7)
        link2 = make_entity("xyz987", session_id, click_count=0)

        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[link1, link2])
            mock_dep.return_value = mock_use_case

            response = await client.get(
                "/api/v1/links",
                cookies={"session_id": session_id},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["links"]) == 2

    @pytest.mark.asyncio
    async def test_estrutura_da_resposta_com_links(self, client):
        """GET /api/v1/links deve retornar os campos corretos em cada link."""
        session_id = "test-session-uuid"
        link = make_entity("abc123", session_id, click_count=5)

        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[link])
            mock_dep.return_value = mock_use_case

            response = await client.get(
                "/api/v1/links",
                cookies={"session_id": session_id},
            )

        assert response.status_code == 200
        data = response.json()
        item = data["links"][0]
        assert "short_code" in item
        assert "original_url" in item
        assert "short_url" in item
        assert "click_count" in item
        assert "created_at" in item
        assert item["short_code"] == "abc123"
        assert item["click_count"] == 5

    @pytest.mark.asyncio
    async def test_com_cookie_mas_sem_links_retorna_lista_vazia(self, client):
        """GET /api/v1/links com cookie mas sem links deve retornar lista vazia."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            response = await client.get(
                "/api/v1/links",
                cookies={"session_id": "sessao-sem-links"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data == {"links": []}

    @pytest.mark.asyncio
    async def test_nao_seta_cookie_na_resposta_de_listagem(self, client):
        """GET /api/v1/links não deve setar cookie na resposta."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            response = await client.get("/api/v1/links")

        assert "set-cookie" not in response.headers


class TestShortenEndpointWithSession:
    """Testes de integração para o comportamento de sessão no POST /api/v1/shorten."""

    @pytest.mark.asyncio
    async def test_sem_cookie_gera_novo_session_id(self, app, client):
        """POST /api/v1/shorten sem cookie deve gerar um novo session_id e setá-lo."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="aB3kZ9",
                    short_url="https://short.app/aB3kZ9",
                    original_url="https://exemplo.com",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/v1/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        # Deve ter setado o cookie session_id
        assert "session_id" in response.cookies

    @pytest.mark.asyncio
    async def test_com_cookie_nao_gera_novo_session_id(self, app, client):
        """POST /api/v1/shorten com cookie existente não deve alterar o cookie."""
        existing_session = "550e8400-e29b-41d4-a716-446655440000"

        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="aB3kZ9",
                    short_url="https://short.app/aB3kZ9",
                    original_url="https://exemplo.com",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/v1/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
                cookies={"session_id": existing_session},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        # NÃO deve ter setado novo cookie (ou o valor deve ser o mesmo)
        if "session_id" in response.cookies:
            assert response.cookies["session_id"] == existing_session

    @pytest.mark.asyncio
    async def test_session_id_e_passado_ao_use_case(self, app, client):
        """POST /api/v1/shorten deve passar o session_id ao use case."""
        existing_session = "550e8400-e29b-41d4-a716-446655440000"

        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="aB3kZ9",
                    short_url="https://short.app/aB3kZ9",
                    original_url="https://exemplo.com",
                )
            )
            mock_dep.return_value = mock_use_case

            await client.post(
                "/api/v1/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
                cookies={"session_id": existing_session},
            )
        app.dependency_overrides.clear()

        # Verifica que o session_id foi passado ao execute
        mock_use_case.execute.assert_called_once()
        call_kwargs = mock_use_case.execute.call_args.kwargs
        assert call_kwargs.get("session_id") == existing_session
