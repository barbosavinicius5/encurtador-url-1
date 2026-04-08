"""Testes unitários para PostgreSQLUrlRepository."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.entities.shortened_url import ShortenedUrl
from app.infrastructure.db.repositories.url_repository import PostgreSQLUrlRepository


def _make_url_model(
    short_code="abc123",
    original_url="https://exemplo.com",
    click_count=0,
    session_id=None,
    deleted_at=None,
    id=1,
):
    model = MagicMock()
    model.short_code = short_code
    model.original_url = original_url
    model.click_count = click_count
    model.session_id = session_id
    model.deleted_at = deleted_at
    model.id = id
    model.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return model


class TestPostgreSQLUrlRepository:
    """Testes para PostgreSQLUrlRepository."""

    @pytest.mark.asyncio
    async def test_save_persiste_url_e_retorna_entidade(self):
        """save() deve persistir e retornar ShortenedUrl com id."""
        session = AsyncMock()
        model = _make_url_model(id=42)
        session.flush = AsyncMock()
        session.refresh = AsyncMock(side_effect=lambda m: None)

        with patch(
            "app.infrastructure.db.repositories.url_repository.ShortenedUrlModel",
            return_value=model,
        ):
            repo = PostgreSQLUrlRepository(session)
            url_entity = ShortenedUrl(
                original_url="https://exemplo.com",
                short_code="abc123",
                session_id="sess-1",
            )
            result = await repo.save(url_entity)

        assert result.short_code == "abc123"
        assert result.original_url == "https://exemplo.com"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_by_short_code_retorna_entidade_quando_existe(self):
        """find_by_short_code() deve retornar entidade quando slug existe."""
        session = AsyncMock()
        model = _make_url_model(short_code="xyz789", click_count=5)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = model
        session.execute = AsyncMock(return_value=result_mock)

        repo = PostgreSQLUrlRepository(session)
        entity = await repo.find_by_short_code("xyz789")

        assert entity is not None
        assert entity.short_code == "xyz789"
        assert entity.click_count == 5

    @pytest.mark.asyncio
    async def test_find_by_short_code_retorna_none_quando_nao_existe(self):
        """find_by_short_code() deve retornar None quando slug não existe."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = PostgreSQLUrlRepository(session)
        entity = await repo.find_by_short_code("naoexiste")

        assert entity is None

    @pytest.mark.asyncio
    async def test_find_by_short_code_click_count_none_vira_zero(self):
        """find_by_short_code() deve converter click_count None para 0."""
        session = AsyncMock()
        model = _make_url_model(short_code="abc", click_count=None)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = model
        session.execute = AsyncMock(return_value=result_mock)

        repo = PostgreSQLUrlRepository(session)
        entity = await repo.find_by_short_code("abc")

        assert entity.click_count == 0

    @pytest.mark.asyncio
    async def test_exists_by_short_code_retorna_true_quando_existe(self):
        """exists_by_short_code() deve retornar True quando slug existe."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = 1
        session.execute = AsyncMock(return_value=result_mock)

        repo = PostgreSQLUrlRepository(session)
        exists = await repo.exists_by_short_code("abc123")

        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_by_short_code_retorna_false_quando_nao_existe(self):
        """exists_by_short_code() deve retornar False quando slug não existe."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = PostgreSQLUrlRepository(session)
        exists = await repo.exists_by_short_code("naoexiste")

        assert exists is False

    @pytest.mark.asyncio
    async def test_increment_click_count_executa_update(self):
        """increment_click_count() deve executar UPDATE e commit."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        repo = PostgreSQLUrlRepository(session)
        await repo.increment_click_count("abc123")

        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_by_session_id_retorna_lista_ordenada(self):
        """find_by_session_id() deve retornar lista de entidades."""
        session = AsyncMock()
        model1 = _make_url_model(short_code="abc", session_id="sess-1", id=1)
        model2 = _make_url_model(short_code="xyz", session_id="sess-1", id=2, click_count=None)
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [model1, model2]
        session.execute = AsyncMock(return_value=result_mock)

        repo = PostgreSQLUrlRepository(session)
        entities = await repo.find_by_session_id("sess-1")

        assert len(entities) == 2
        assert entities[0].short_code == "abc"
        assert entities[1].click_count == 0
