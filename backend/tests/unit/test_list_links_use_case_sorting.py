"""Testes unitários para o ListLinksUseCase - ordenação dinâmica (US-002 T001-BE)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.list_links_use_case import ListLinksUseCase
from app.domain.entities.shortened_url import ShortenedUrl


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
        created_at=created_at or datetime.now(UTC),
        click_count=click_count,
        session_id=session_id,
    )


class TestListLinksUseCaseSorting:
    """Testes para ordenação dinâmica no use case de listagem."""

    @pytest.mark.asyncio
    async def test_repassa_sort_by_ao_repositorio(self):
        """Deve repassar sort_by=click_count ao repositório."""
        session_id = "test-session-uuid"
        repo = AsyncMock()
        repo.find_by_session_id.return_value = []

        use_case = ListLinksUseCase(repository=repo)
        await use_case.execute(
            session_id=session_id,
            sort_by="click_count",
            sort_order="asc",
        )

        repo.find_by_session_id.assert_called_once_with(
            session_id,
            sort_by="click_count",
            sort_order="asc",
        )

    @pytest.mark.asyncio
    async def test_repassa_sort_by_created_at_ao_repositorio(self):
        """Deve repassar sort_by=created_at ao repositório."""
        session_id = "test-session-uuid"
        repo = AsyncMock()
        repo.find_by_session_id.return_value = []

        use_case = ListLinksUseCase(repository=repo)
        await use_case.execute(
            session_id=session_id,
            sort_by="created_at",
            sort_order="asc",
        )

        repo.find_by_session_id.assert_called_once_with(
            session_id,
            sort_by="created_at",
            sort_order="asc",
        )

    @pytest.mark.asyncio
    async def test_default_sort_retrocompativel(self):
        """Deve usar defaults created_at DESC para retrocompatibilidade."""
        session_id = "test-session-uuid"
        repo = AsyncMock()
        repo.find_by_session_id.return_value = []

        use_case = ListLinksUseCase(repository=repo)
        await use_case.execute(session_id=session_id)

        repo.find_by_session_id.assert_called_once_with(
            session_id,
            sort_by="created_at",
            sort_order="desc",
        )

    @pytest.mark.asyncio
    async def test_repassa_sort_order_desc_ao_repositorio(self):
        """Deve repassar sort_order=desc ao repositório."""
        session_id = "test-session-uuid"
        repo = AsyncMock()
        repo.find_by_session_id.return_value = []

        use_case = ListLinksUseCase(repository=repo)
        await use_case.execute(
            session_id=session_id,
            sort_by="click_count",
            sort_order="desc",
        )

        repo.find_by_session_id.assert_called_once_with(
            session_id,
            sort_by="click_count",
            sort_order="desc",
        )

    @pytest.mark.asyncio
    async def test_retorna_lista_vazia_quando_session_id_none_com_sort_params(self):
        """Deve retornar lista vazia mesmo com parâmetros de ordenação quando session_id é None."""
        repo = AsyncMock()
        use_case = ListLinksUseCase(repository=repo)

        result = await use_case.execute(
            session_id=None,
            sort_by="click_count",
            sort_order="asc",
        )

        assert result == []
        repo.find_by_session_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_retorna_links_com_sort_by_click_count_asc(self):
        """Deve retornar links ordenados por click_count ASC conforme retornado pelo repositório."""
        session_id = "test-session"
        link_less = make_entity("ghi789", session_id, click_count=5)
        link_middle = make_entity("abc123", session_id, click_count=10)
        link_most = make_entity("def456", session_id, click_count=50)

        repo = AsyncMock()
        repo.find_by_session_id.return_value = [link_less, link_middle, link_most]

        use_case = ListLinksUseCase(repository=repo)
        result = await use_case.execute(
            session_id=session_id,
            sort_by="click_count",
            sort_order="asc",
        )

        assert len(result) == 3
        assert result[0].click_count == 5
        assert result[1].click_count == 10
        assert result[2].click_count == 50

    @pytest.mark.asyncio
    async def test_retorna_links_com_sort_by_click_count_desc(self):
        """Deve retornar links ordenados por click_count DESC conforme retornado pelo repositório."""
        session_id = "test-session"
        link_most = make_entity("def456", session_id, click_count=50)
        link_middle = make_entity("abc123", session_id, click_count=10)
        link_less = make_entity("ghi789", session_id, click_count=5)

        repo = AsyncMock()
        repo.find_by_session_id.return_value = [link_most, link_middle, link_less]

        use_case = ListLinksUseCase(repository=repo)
        result = await use_case.execute(
            session_id=session_id,
            sort_by="click_count",
            sort_order="desc",
        )

        assert len(result) == 3
        assert result[0].click_count == 50
        assert result[1].click_count == 10
        assert result[2].click_count == 5
