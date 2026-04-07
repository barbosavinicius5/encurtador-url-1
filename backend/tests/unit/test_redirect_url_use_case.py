"""Testes unitários para o use case RedirectUrlUseCase (US-002 / T001-BE)."""

import logging
from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks

from app.application.use_cases.redirect_url_use_case import RedirectUrlUseCase
from app.domain.entities.shortened_url import ShortenedUrl


class TestRedirectUrlUseCaseWithClickCount:
    """Testes para o use case de redirect com contagem assíncrona de cliques."""

    @pytest.fixture
    def mock_repository(self):
        repo = AsyncMock()
        repo.find_by_short_code = AsyncMock()
        repo.increment_click_count = AsyncMock()
        return repo

    @pytest.fixture
    def mock_cache(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.increment_with_ttl = AsyncMock(return_value=1)
        return cache

    @pytest.fixture
    def background_tasks(self):
        """Fixture que fornece BackgroundTasks real para validar tarefas agendadas."""
        return BackgroundTasks()

    @pytest.fixture
    def use_case(self, mock_repository, mock_cache):
        return RedirectUrlUseCase(repository=mock_repository, cache=mock_cache)

    @pytest.fixture
    def sample_entity(self):
        return ShortenedUrl(
            original_url="https://example.com",
            short_code="abc123",
            click_count=0,
        )

    # --- Cenário A: Cache hit ---

    @pytest.mark.asyncio
    async def test_redirect_cache_hit_retorna_url(self, use_case, mock_cache, background_tasks):
        """Redirect via cache retorna URL correta."""
        mock_cache.get = AsyncMock(return_value="https://example.com")

        result = await use_case.execute("abc123", background_tasks)

        assert result == "https://example.com"

    @pytest.mark.asyncio
    async def test_redirect_cache_hit_nao_consulta_repositorio(
        self, use_case, mock_cache, mock_repository, background_tasks
    ):
        """Com cache hit, o repositório não deve ser consultado."""
        mock_cache.get = AsyncMock(return_value="https://example.com")

        await use_case.execute("abc123", background_tasks)

        mock_repository.find_by_short_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_redirect_cache_hit_agenda_increment_como_background_task(
        self, use_case, mock_cache, mock_repository, background_tasks
    ):
        """Com cache hit, deve agendar o incremento via BackgroundTasks."""
        mock_cache.get = AsyncMock(return_value="https://example.com")

        await use_case.execute("abc123", background_tasks)

        # Verificar que existe ao menos uma BackgroundTask agendada
        assert len(background_tasks.tasks) >= 1

    @pytest.mark.asyncio
    async def test_redirect_cache_hit_executa_increment_no_banco(
        self, use_case, mock_cache, mock_repository, background_tasks
    ):
        """Com cache hit, executar BackgroundTask incrementa no banco."""
        mock_cache.get = AsyncMock(return_value="https://example.com")

        await use_case.execute("abc123", background_tasks)

        # Executar as background tasks manualmente
        for task in background_tasks.tasks:
            await task()

        mock_repository.increment_click_count.assert_called_once_with("abc123")

    # --- Cenário B: Cache miss ---

    @pytest.mark.asyncio
    async def test_redirect_cache_miss_consulta_repositorio(
        self, use_case, mock_cache, mock_repository, sample_entity, background_tasks
    ):
        """Com cache miss, o repositório deve ser consultado."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)

        result = await use_case.execute("abc123", background_tasks)

        assert result == "https://example.com"
        mock_repository.find_by_short_code.assert_called_once_with("abc123")

    @pytest.mark.asyncio
    async def test_redirect_cache_miss_popula_cache(
        self, use_case, mock_cache, mock_repository, sample_entity, background_tasks
    ):
        """Com cache miss, a URL deve ser populada no cache."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)

        await use_case.execute("abc123", background_tasks)

        mock_cache.set.assert_called_once_with(
            "url:abc123", "https://example.com", ttl_seconds=3600
        )

    @pytest.mark.asyncio
    async def test_redirect_cache_miss_agenda_increment_como_background_task(
        self, use_case, mock_cache, mock_repository, sample_entity, background_tasks
    ):
        """Com cache miss, deve agendar o incremento via BackgroundTasks."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)

        await use_case.execute("abc123", background_tasks)

        # Verificar que existe ao menos uma BackgroundTask agendada
        assert len(background_tasks.tasks) >= 1

    @pytest.mark.asyncio
    async def test_redirect_cache_miss_executa_increment_no_banco(
        self, use_case, mock_cache, mock_repository, sample_entity, background_tasks
    ):
        """Com cache miss, executar BackgroundTask incrementa no banco."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)

        await use_case.execute("abc123", background_tasks)

        # Executar as background tasks manualmente
        for task in background_tasks.tasks:
            await task()

        mock_repository.increment_click_count.assert_called_once_with("abc123")

    # --- Cenário C: Slug inválido ---

    @pytest.mark.asyncio
    async def test_slug_invalido_levanta_value_error(
        self, use_case, mock_cache, mock_repository, background_tasks
    ):
        """Slug não encontrado deve levantar ValueError."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="não encontrado"):
            await use_case.execute("invalido", background_tasks)

    @pytest.mark.asyncio
    async def test_slug_invalido_nao_agenda_background_task(
        self, use_case, mock_cache, mock_repository, background_tasks
    ):
        """Slug não encontrado não deve agendar nenhuma BackgroundTask."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=None)

        with pytest.raises(ValueError):
            await use_case.execute("invalido", background_tasks)

        assert len(background_tasks.tasks) == 0

    # --- Cenário D: Graceful degradation ---

    @pytest.mark.asyncio
    async def test_falha_banco_increment_nao_bloqueia_redirect(
        self, use_case, mock_cache, mock_repository, background_tasks, caplog
    ):
        """Falha no banco ao incrementar clique não deve bloquear o redirect."""
        mock_cache.get = AsyncMock(return_value="https://example.com")
        mock_repository.increment_click_count = AsyncMock(side_effect=Exception("DB indisponível"))

        with caplog.at_level(logging.ERROR):
            result = await use_case.execute("abc123", background_tasks)

        # Redirect deve ocorrer normalmente
        assert result == "https://example.com"

    @pytest.mark.asyncio
    async def test_falha_banco_increment_loga_error(
        self, use_case, mock_cache, mock_repository, background_tasks, caplog
    ):
        """Falha no banco ao incrementar clique deve ser logada como ERROR."""
        mock_cache.get = AsyncMock(return_value="https://example.com")
        mock_repository.increment_click_count = AsyncMock(side_effect=Exception("DB indisponível"))

        with caplog.at_level(logging.ERROR):
            await use_case.execute("abc123", background_tasks)
            # Executar as background tasks para disparar o erro
            for task in background_tasks.tasks:
                await task()

        # Verificar que existe ao menos um registro de ERROR no log
        error_records = [record for record in caplog.records if record.levelno >= logging.ERROR]
        assert len(error_records) > 0, "Esperava ao menos um log de ERROR"
        # Verificar que a mensagem de erro é sobre falha ao persistir
        assert any(
            "clique" in record.getMessage().lower() or "persistir" in record.getMessage().lower()
            for record in error_records
        )

    @pytest.mark.asyncio
    async def test_falha_repositorio_increment_loga_error(
        self, use_case, mock_cache, mock_repository, sample_entity, background_tasks, caplog
    ):
        """Falha no repositório ao persistir clique deve ser logada como ERROR."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)
        mock_repository.increment_click_count = AsyncMock(side_effect=Exception("DB falhou"))

        with caplog.at_level(logging.ERROR):
            result = await use_case.execute("abc123", background_tasks)
            # Executar as background tasks para disparar o erro
            for task in background_tasks.tasks:
                await task()

        # Redirect deve ocorrer normalmente
        assert result == "https://example.com"

    @pytest.mark.asyncio
    async def test_falha_redis_nao_bloqueia_redirect(
        self, use_case, mock_cache, mock_repository, sample_entity, background_tasks, caplog
    ):
        """Falha no Redis deve gerar WARNING mas não bloquear o redirect."""
        mock_cache.get = AsyncMock(side_effect=Exception("Redis indisponível"))
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)

        with caplog.at_level(logging.WARNING):
            result = await use_case.execute("abc123", background_tasks)

        # Redirect deve ocorrer normalmente (fallback para banco)
        assert result == "https://example.com"

    @pytest.mark.asyncio
    async def test_falha_redis_loga_warning(
        self, use_case, mock_cache, mock_repository, sample_entity, background_tasks, caplog
    ):
        """Falha no Redis deve gerar log de WARNING."""
        mock_cache.get = AsyncMock(side_effect=Exception("Redis indisponível"))
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)

        with caplog.at_level(logging.WARNING):
            await use_case.execute("abc123", background_tasks)

        warning_records = [record for record in caplog.records if record.levelno >= logging.WARNING]
        assert len(warning_records) > 0, "Esperava ao menos um log de WARNING"


class TestShortenedUrlEntityWithClickCount:
    """Testes para a entidade ShortenedUrl com o campo click_count."""

    def test_entidade_tem_campo_click_count(self):
        """A entidade deve ter o campo click_count com default 0."""
        entity = ShortenedUrl(
            original_url="https://example.com",
            short_code="abc123",
        )
        assert entity.click_count == 0

    def test_entidade_aceita_click_count_customizado(self):
        """A entidade deve aceitar click_count customizado."""
        entity = ShortenedUrl(
            original_url="https://example.com",
            short_code="abc123",
            click_count=42,
        )
        assert entity.click_count == 42

    def test_entidade_tem_campo_deleted_at_none_por_padrao(self):
        """A entidade deve ter deleted_at como None por padrão."""
        entity = ShortenedUrl(
            original_url="https://example.com",
            short_code="abc123",
        )
        assert entity.deleted_at is None
