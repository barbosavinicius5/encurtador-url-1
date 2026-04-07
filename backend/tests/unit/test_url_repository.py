"""Testes unitários para o repositório PostgreSQLUrlRepository (US-002 / T001-BE)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.shortened_url import ShortenedUrl
from app.infrastructure.db.repositories.url_repository import PostgreSQLUrlRepository


class TestPostgreSQLUrlRepositoryIncrementClickCount:
    """Testes para o método increment_click_count do repositório."""

    @pytest.fixture
    def mock_session(self):
        """Fixture que cria um AsyncSession mock."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return PostgreSQLUrlRepository(session=mock_session)

    @pytest.mark.asyncio
    async def test_increment_click_count_executa_update(self, repository, mock_session):
        """increment_click_count deve executar um UPDATE no banco."""
        await repository.increment_click_count("abc123")

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_click_count_faz_commit(self, repository, mock_session):
        """increment_click_count deve realizar commit após o UPDATE."""
        await repository.increment_click_count("abc123")

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_click_count_nao_levanta_excecao_em_sucesso(
        self, repository, mock_session
    ):
        """increment_click_count não deve levantar exceção em caso de sucesso."""
        # Não deve levantar exceção
        await repository.increment_click_count("abc123")

    @pytest.mark.asyncio
    async def test_increment_click_count_propaga_excecao_do_banco(self, repository, mock_session):
        """increment_click_count deve propagar exceções do banco de dados."""
        mock_session.execute = AsyncMock(side_effect=Exception("DB erro"))

        with pytest.raises(Exception, match="DB erro"):
            await repository.increment_click_count("abc123")


class TestPostgreSQLUrlRepositoryFindByShortCode:
    """Testes para o método find_by_short_code do repositório."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return PostgreSQLUrlRepository(session=mock_session)

    @pytest.mark.asyncio
    async def test_find_by_short_code_retorna_none_se_nao_existe(self, repository, mock_session):
        """find_by_short_code deve retornar None se não encontrado."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_short_code("invalido")

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_short_code_retorna_entidade_se_existe(self, repository, mock_session):
        """find_by_short_code deve retornar a entidade se encontrada."""
        mock_model = MagicMock()
        mock_model.original_url = "https://example.com"
        mock_model.short_code = "abc123"
        mock_model.created_at = datetime.now(UTC)
        mock_model.id = 1
        mock_model.click_count = 5
        mock_model.deleted_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_short_code("abc123")

        assert result is not None
        assert isinstance(result, ShortenedUrl)
        assert result.original_url == "https://example.com"
        assert result.short_code == "abc123"
        assert result.click_count == 5

    @pytest.mark.asyncio
    async def test_find_by_short_code_retorna_click_count_zero_se_none(
        self, repository, mock_session
    ):
        """find_by_short_code deve retornar click_count=0 se o campo for None no banco."""
        mock_model = MagicMock()
        mock_model.original_url = "https://example.com"
        mock_model.short_code = "abc123"
        mock_model.created_at = datetime.now(UTC)
        mock_model.id = 1
        mock_model.click_count = None
        mock_model.deleted_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_short_code("abc123")

        assert result is not None
        assert result.click_count == 0
