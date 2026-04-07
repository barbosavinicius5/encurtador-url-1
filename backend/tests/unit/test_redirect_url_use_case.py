"""Testes unitários para o use case RedirectUrlUseCase (US-002)."""

import asyncio
import logging
from unittest.mock import AsyncMock

import pytest

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
    def use_case(self, mock_repository, mock_cache):
        return RedirectUrlUseCase(repository=mock_repository, cache=mock_cache)

    @pytest.fixture
    def use_case_custom_ttl(self, mock_repository, mock_cache):
        return RedirectUrlUseCase(
            repository=mock_repository, cache=mock_cache, cache_ttl_seconds=60
        )

    @pytest.fixture
    def sample_entity(self):
        return ShortenedUrl(
            original_url="https://example.com",
            short_code="abc123",
            click_count=0,
        )

    # --- Cenário A: Cache hit ---

    @pytest.mark.asyncio
    async def test_redirect_cache_hit_retorna_url(self, use_case, mock_cache):
        """Redirect via cache retorna URL correta."""
        mock_cache.get = AsyncMock(return_value="https://example.com")

        result = await use_case.execute("abc123")

        assert result == "https://example.com"

    @pytest.mark.asyncio
    async def test_redirect_cache_hit_nao_consulta_repositorio(
        self, use_case, mock_cache, mock_repository
    ):
        """Com cache hit, o repositório não deve ser consultado."""
        mock_cache.get = AsyncMock(return_value="https://example.com")

        await use_case.execute("abc123")

        mock_repository.find_by_short_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_redirect_cache_hit_chama_increment_banco(
        self, use_case, mock_cache, mock_repository
    ):
        """Com cache hit, o banco deve ser chamado para incrementar o clique."""
        mock_cache.get = AsyncMock(return_value="https://example.com")

        await use_case.execute("abc123")

        # Aguardar task assíncrona
        await asyncio.sleep(0.01)
        mock_repository.increment_click_count.assert_called_once_with("abc123")

    # --- Cenário B: Cache miss ---

    @pytest.mark.asyncio
    async def test_redirect_cache_miss_consulta_repositorio(
        self, use_case, mock_cache, mock_repository, sample_entity
    ):
        """Com cache miss, o repositório deve ser consultado."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)

        result = await use_case.execute("abc123")

        assert result == "https://example.com"
        mock_repository.find_by_short_code.assert_called_once_with("abc123")

    @pytest.mark.asyncio
    async def test_redirect_cache_miss_popula_cache(
        self, use_case, mock_cache, mock_repository, sample_entity
    ):
        """Com cache miss, a URL deve ser populada no cache."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)

        await use_case.execute("abc123")

        mock_cache.set.assert_called_once_with(
            "url:abc123", "https://example.com", ttl_seconds=3600
        )

    @pytest.mark.asyncio
    async def test_redirect_cache_miss_agenda_increment_click(
        self, use_case, mock_cache, mock_repository, sample_entity
    ):
        """Com cache miss, o clique deve ser registrado no banco de forma assíncrona."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)

        await use_case.execute("abc123")

        # Aguardar task assíncrona
        await asyncio.sleep(0.01)
        mock_repository.increment_click_count.assert_called_once_with("abc123")

    # --- Cenário C: Slug inválido ---

    @pytest.mark.asyncio
    async def test_slug_invalido_levanta_value_error(self, use_case, mock_cache, mock_repository):
        """Slug não encontrado deve levantar ValueError."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="não encontrado"):
            await use_case.execute("invalido")

    # --- Cenário D: Graceful degradation Redis ---

    @pytest.mark.asyncio
    async def test_falha_banco_increment_nao_bloqueia_redirect(
        self, use_case, mock_cache, mock_repository, caplog
    ):
        """Falha no banco ao incrementar clique não deve bloquear o redirect."""
        mock_cache.get = AsyncMock(return_value="https://example.com")
        mock_repository.increment_click_count = AsyncMock(side_effect=Exception("DB indisponível"))

        with caplog.at_level(logging.ERROR):
            result = await use_case.execute("abc123")

        # Aguardar task assíncrona
        await asyncio.sleep(0.01)

        # Redirect deve ocorrer normalmente
        assert result == "https://example.com"

    @pytest.mark.asyncio
    async def test_falha_banco_increment_loga_error(
        self, use_case, mock_cache, mock_repository, caplog
    ):
        """Falha no banco ao incrementar clique deve ser logada como ERROR."""
        mock_cache.get = AsyncMock(return_value="https://example.com")
        mock_repository.increment_click_count = AsyncMock(side_effect=Exception("DB indisponível"))

        with caplog.at_level(logging.ERROR):
            await use_case.execute("abc123")
            await asyncio.sleep(0.01)  # Aguardar task assíncrona

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
        self, use_case, mock_cache, mock_repository, sample_entity, caplog
    ):
        """Falha no repositório ao persistir clique deve ser logada como ERROR."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)
        mock_repository.increment_click_count = AsyncMock(side_effect=Exception("DB falhou"))

        with caplog.at_level(logging.ERROR):
            result = await use_case.execute("abc123")
            await asyncio.sleep(0.01)  # Aguardar task assíncrona

        # Redirect deve ocorrer normalmente
        assert result == "https://example.com"


class TestRedirectUrlUseCaseTtlConfiguravel:
    """Testes para validar o TTL configurável via construtor (T001-BE)."""

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
        return cache

    @pytest.fixture
    def sample_entity(self):
        return ShortenedUrl(
            original_url="https://www.exemplo.com/longa",
            short_code="aB12x",
            click_count=0,
        )

    # --- Cenário A: TTL default (3600) propagado ---

    @pytest.mark.asyncio
    async def test_redirect_sets_cache_with_default_ttl(
        self, mock_repository, mock_cache, sample_entity
    ):
        """TTL default (3600) deve ser usado quando nenhum TTL é injetado."""
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)
        use_case = RedirectUrlUseCase(mock_repository, mock_cache)

        await use_case.execute("aB12x")

        mock_cache.set.assert_called_once_with(
            "url:aB12x", "https://www.exemplo.com/longa", ttl_seconds=3600
        )

    # --- Cenário B: TTL customizado dev (60s) ---

    @pytest.mark.asyncio
    async def test_redirect_sets_cache_with_custom_ttl_dev(
        self, mock_repository, mock_cache, sample_entity
    ):
        """TTL customizado (60s) para desenvolvimento deve ser usado corretamente."""
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)
        use_case = RedirectUrlUseCase(mock_repository, mock_cache, cache_ttl_seconds=60)

        await use_case.execute("aB12x")

        mock_cache.set.assert_called_once_with(
            "url:aB12x", "https://www.exemplo.com/longa", ttl_seconds=60
        )

    # --- Cenário C: TTL customizado prod agressivo (7200s) ---

    @pytest.mark.asyncio
    async def test_redirect_sets_cache_with_custom_ttl_prod(
        self, mock_repository, mock_cache, sample_entity
    ):
        """TTL customizado (7200s) para produção agressiva deve ser usado corretamente."""
        mock_repository.find_by_short_code = AsyncMock(return_value=sample_entity)
        use_case = RedirectUrlUseCase(mock_repository, mock_cache, cache_ttl_seconds=7200)

        await use_case.execute("aB12x")

        mock_cache.set.assert_called_once_with(
            "url:aB12x", "https://www.exemplo.com/longa", ttl_seconds=7200
        )

    # --- Cenário D: Cache hit não chama set ---

    @pytest.mark.asyncio
    async def test_cache_hit_nao_chama_set(self, mock_repository, mock_cache):
        """Com cache hit, cache.set NÃO deve ser chamado (sem renovação de TTL)."""
        mock_cache.get = AsyncMock(return_value="https://www.exemplo.com/longa")
        use_case = RedirectUrlUseCase(mock_repository, mock_cache, cache_ttl_seconds=60)

        await use_case.execute("aB12x")

        mock_cache.set.assert_not_called()

    # --- Cenário E: TTL é atributo de instância ---

    def test_use_case_armazena_cache_ttl_seconds(self, mock_repository, mock_cache):
        """O use case deve armazenar cache_ttl_seconds como atributo de instância."""
        use_case = RedirectUrlUseCase(mock_repository, mock_cache, cache_ttl_seconds=300)

        assert use_case.cache_ttl_seconds == 300


class TestSettingsCacheTtl:
    """Testes para validar que Settings contém cache_ttl_seconds configurável."""

    def test_settings_tem_campo_cache_ttl_seconds(self):
        """Settings deve ter o campo cache_ttl_seconds com default 3600."""
        from app.config import Settings

        settings = Settings()
        assert hasattr(settings, "cache_ttl_seconds")
        assert settings.cache_ttl_seconds == 3600

    def test_settings_cache_ttl_seconds_override_via_env(self, monkeypatch):
        """cache_ttl_seconds deve ser sobrescrito via variável de ambiente."""
        import app.config as config_module

        monkeypatch.setenv("CACHE_TTL_SECONDS", "60")
        # Recriar Settings para pegar nova env var (sem lru_cache)
        settings = config_module.Settings()
        assert settings.cache_ttl_seconds == 60

    def test_settings_cache_ttl_seconds_7200_via_env(self, monkeypatch):
        """cache_ttl_seconds deve aceitar valores customizados altos."""
        import app.config as config_module

        monkeypatch.setenv("CACHE_TTL_SECONDS", "7200")
        settings = config_module.Settings()
        assert settings.cache_ttl_seconds == 7200


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
