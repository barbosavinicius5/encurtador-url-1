"""Testes de integração para ordenação dinâmica no endpoint GET /api/links (US-002 T001-BE)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.entities.shortened_url import ShortenedUrl
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def make_entity(
    short_code: str,
    session_id: str,
    click_count: int = 0,
    created_at: datetime | None = None,
) -> ShortenedUrl:
    """Helper para criar entidades de teste."""
    return ShortenedUrl(
        original_url=f"https://example.com/{short_code}",
        short_code=short_code,
        created_at=created_at or datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        click_count=click_count,
        session_id=session_id,
    )


SESSION_ID = "550e8400-e29b-41d4-a716-446655440000"


class TestListLinksEndpointSorting:
    """Testes de integração para os query params de ordenação."""

    @pytest.mark.asyncio
    async def test_sort_by_click_count_asc_retorna_200(self, client):
        """GET /api/links?sort_by=click_count&sort_order=asc deve retornar HTTP 200."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            response = await client.get(
                "/api/links",
                params={"sort_by": "click_count", "sort_order": "asc"},
                cookies={"session_id": SESSION_ID},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_sort_by_click_count_desc_retorna_200(self, client):
        """GET /api/links?sort_by=click_count&sort_order=desc deve retornar HTTP 200."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            response = await client.get(
                "/api/links",
                params={"sort_by": "click_count", "sort_order": "desc"},
                cookies={"session_id": SESSION_ID},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_sort_by_created_at_asc_retorna_200(self, client):
        """GET /api/links?sort_by=created_at&sort_order=asc deve retornar HTTP 200."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            response = await client.get(
                "/api/links",
                params={"sort_by": "created_at", "sort_order": "asc"},
                cookies={"session_id": SESSION_ID},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_sem_params_retorna_200_retrocompativel(self, client):
        """GET /api/links sem query params deve retornar HTTP 200 (retrocompatibilidade)."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            response = await client.get(
                "/api/links",
                cookies={"session_id": SESSION_ID},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_sort_by_invalido_retorna_422(self, client):
        """GET /api/links?sort_by=invalid_field deve retornar HTTP 422."""
        response = await client.get(
            "/api/links",
            params={"sort_by": "invalid_field"},
            cookies={"session_id": SESSION_ID},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_sort_order_invalido_retorna_422(self, client):
        """GET /api/links?sort_order=random deve retornar HTTP 422."""
        response = await client.get(
            "/api/links",
            params={"sort_order": "random"},
            cookies={"session_id": SESSION_ID},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_sort_by_invalido_corpo_contem_mensagem_de_validacao(self, client):
        """HTTP 422 deve conter mensagem indicando valores aceitos para sort_by."""
        response = await client.get(
            "/api/links",
            params={"sort_by": "invalid_field"},
            cookies={"session_id": SESSION_ID},
        )

        assert response.status_code == 422
        body = response.text
        # A mensagem deve mencionar os valores aceitos
        assert "created_at" in body or "click_count" in body

    @pytest.mark.asyncio
    async def test_use_case_recebe_sort_params_corretos(self, client):
        """O use case deve ser chamado com os parâmetros de ordenação corretos."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            await client.get(
                "/api/links",
                params={"sort_by": "click_count", "sort_order": "asc"},
                cookies={"session_id": SESSION_ID},
            )

        mock_use_case.execute.assert_called_once()
        call_kwargs = mock_use_case.execute.call_args.kwargs
        assert call_kwargs.get("sort_by") == "click_count"
        assert call_kwargs.get("sort_order") == "asc"

    @pytest.mark.asyncio
    async def test_use_case_recebe_defaults_quando_sem_params(self, client):
        """O use case deve ser chamado com defaults quando query params não são enviados."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            await client.get(
                "/api/links",
                cookies={"session_id": SESSION_ID},
            )

        mock_use_case.execute.assert_called_once()
        call_kwargs = mock_use_case.execute.call_args.kwargs
        assert call_kwargs.get("sort_by") == "created_at"
        assert call_kwargs.get("sort_order") == "desc"

    @pytest.mark.asyncio
    async def test_retorna_links_ordenados_por_click_count_asc(self, client):
        """Deve retornar links na ordem fornecida pelo use case (click_count ASC)."""
        link_less = make_entity("ghi789", SESSION_ID, click_count=5)
        link_middle = make_entity("abc123", SESSION_ID, click_count=10)
        link_most = make_entity("def456", SESSION_ID, click_count=50)

        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[link_less, link_middle, link_most])
            mock_dep.return_value = mock_use_case

            response = await client.get(
                "/api/links",
                params={"sort_by": "click_count", "sort_order": "asc"},
                cookies={"session_id": SESSION_ID},
            )

        assert response.status_code == 200
        data = response.json()
        links = data["links"]
        assert len(links) == 3
        assert links[0]["click_count"] == 5
        assert links[0]["short_code"] == "ghi789"
        assert links[2]["click_count"] == 50
        assert links[2]["short_code"] == "def456"

    @pytest.mark.asyncio
    async def test_sessao_sem_links_com_sort_params_retorna_lista_vazia(self, client):
        """Sessão sem links com params de ordenação deve retornar [] com HTTP 200."""
        with patch("app.infrastructure.di.container.get_list_links_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(return_value=[])
            mock_dep.return_value = mock_use_case

            response = await client.get(
                "/api/links",
                params={"sort_by": "click_count", "sort_order": "asc"},
                cookies={"session_id": SESSION_ID},
            )

        assert response.status_code == 200
        data = response.json()
        assert data == {"links": []}
