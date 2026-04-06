"""Testes unitários para o ListLinksUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.list_links_use_case import ListLinksUseCase
from app.domain.entities.shortened_url import ShortenedUrl


def make_entity(short_code: str, session_id: str, click_count: int = 0) -> ShortenedUrl:
    """Helper para criar entidades de teste."""
    return ShortenedUrl(
        original_url=f"https://example.com/{short_code}",
        short_code=short_code,
        created_at=datetime.now(UTC),
        click_count=click_count,
        session_id=session_id,
    )


class TestListLinksUseCase:
    """Testes para o use case de listagem de links."""

    @pytest.mark.asyncio
    async def test_retorna_lista_vazia_quando_session_id_e_none(self):
        """Deve retornar lista vazia quando session_id é None."""
        repo = AsyncMock()
        use_case = ListLinksUseCase(repository=repo)

        result = await use_case.execute(session_id=None)

        assert result == []
        repo.find_by_session_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_retorna_lista_vazia_quando_session_id_e_string_vazia(self):
        """Deve retornar lista vazia quando session_id é string vazia."""
        repo = AsyncMock()
        use_case = ListLinksUseCase(repository=repo)

        result = await use_case.execute(session_id="")

        assert result == []
        repo.find_by_session_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_retorna_links_da_sessao(self):
        """Deve retornar os links associados ao session_id."""
        session_id = "test-session-uuid-1234"
        link1 = make_entity("abc123", session_id, click_count=7)
        link2 = make_entity("xyz987", session_id, click_count=0)

        repo = AsyncMock()
        repo.find_by_session_id.return_value = [link1, link2]

        use_case = ListLinksUseCase(repository=repo)
        result = await use_case.execute(session_id=session_id)

        assert len(result) == 2
        assert result[0].short_code == "abc123"
        assert result[1].short_code == "xyz987"
        repo.find_by_session_id.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_retorna_lista_vazia_quando_sessao_nao_tem_links(self):
        """Deve retornar lista vazia quando a sessão não tem links."""
        repo = AsyncMock()
        repo.find_by_session_id.return_value = []

        use_case = ListLinksUseCase(repository=repo)
        result = await use_case.execute(session_id="sessao-sem-links")

        assert result == []
        repo.find_by_session_id.assert_called_once_with("sessao-sem-links")

    @pytest.mark.asyncio
    async def test_repassa_session_id_ao_repositorio(self):
        """Deve repassar o session_id recebido ao repositório sem modificação."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        repo = AsyncMock()
        repo.find_by_session_id.return_value = []

        use_case = ListLinksUseCase(repository=repo)
        await use_case.execute(session_id=session_id)

        repo.find_by_session_id.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_retorna_click_count_correto(self):
        """Deve retornar o click_count real de cada link."""
        session_id = "test-session"
        link = make_entity("abc123", session_id, click_count=42)

        repo = AsyncMock()
        repo.find_by_session_id.return_value = [link]

        use_case = ListLinksUseCase(repository=repo)
        result = await use_case.execute(session_id=session_id)

        assert result[0].click_count == 42
