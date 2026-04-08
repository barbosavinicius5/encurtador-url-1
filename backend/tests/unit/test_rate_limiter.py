"""Testes unitários para rate_limiter e brute_force_protection."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.infrastructure.middleware.rate_limiter import rate_limit_by_api_key, rate_limit_by_ip


def _make_settings(**kwargs) -> Settings:
    defaults = dict(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        redis_url="redis://localhost:6379/0",
        rate_limit_requests=10,
        rate_limit_window_seconds=60,
        api_rate_limit_requests=60,
        brute_force_detection_window_seconds=300,
        brute_force_block_seconds=3600,
        brute_force_threshold_multiplier=3,
    )
    defaults.update(kwargs)
    return Settings(**defaults)


def _make_request(host="127.0.0.1"):
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = host
    request.url.path = "/test"
    return request


class TestRateLimitByIp:
    """Testes para rate_limit_by_ip dependency."""

    @pytest.mark.asyncio
    async def test_permite_requisicao_dentro_do_limite(self):
        """Deve permitir requisição quando contagem está dentro do limite."""
        request = _make_request()
        settings = _make_settings()

        with patch("app.infrastructure.middleware.rate_limiter.RedisClient") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.increment_with_ttl = AsyncMock(return_value=5)
            mock_redis_cls.return_value = mock_redis

            # Não deve lançar exceção
            await rate_limit_by_ip(request=request, settings=settings)

    @pytest.mark.asyncio
    async def test_bloqueia_requisicao_acima_do_limite(self):
        """Deve lançar HTTPException 429 quando limite é ultrapassado."""
        request = _make_request()
        settings = _make_settings(rate_limit_requests=10)

        with patch("app.infrastructure.middleware.rate_limiter.RedisClient") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.increment_with_ttl = AsyncMock(return_value=11)
            mock_redis.get_ttl = AsyncMock(return_value=30)
            mock_redis.increment_with_ttl = AsyncMock(side_effect=[11, 1])
            mock_redis_cls.return_value = mock_redis

            with pytest.raises(HTTPException) as exc_info:
                await rate_limit_by_ip(request=request, settings=settings)

        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_fail_open_quando_redis_indisponivel(self):
        """Deve permitir requisição quando Redis está indisponível (fail-open)."""
        request = _make_request()
        settings = _make_settings()

        with patch("app.infrastructure.middleware.rate_limiter.RedisClient") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.increment_with_ttl = AsyncMock(
                side_effect=Exception("Redis connection error")
            )
            mock_redis_cls.return_value = mock_redis

            # Não deve lançar exceção — fail open
            await rate_limit_by_ip(request=request, settings=settings)

    @pytest.mark.asyncio
    async def test_sem_client_usa_unknown_como_ip(self):
        """Deve usar 'unknown' como IP quando request.client é None."""
        request = MagicMock()
        request.client = None
        request.url.path = "/test"
        settings = _make_settings()

        with patch("app.infrastructure.middleware.rate_limiter.RedisClient") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.increment_with_ttl = AsyncMock(return_value=1)
            mock_redis_cls.return_value = mock_redis

            # Não deve lançar exceção
            await rate_limit_by_ip(request=request, settings=settings)


class TestRateLimitByApiKey:
    """Testes para rate_limit_by_api_key dependency."""

    @pytest.mark.asyncio
    async def test_permite_requisicao_dentro_do_limite(self):
        """Deve permitir requisição quando contagem está dentro do limite por API key."""
        settings = _make_settings(api_rate_limit_requests=60)

        with patch("app.infrastructure.middleware.rate_limiter.RedisClient") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.increment_with_ttl = AsyncMock(return_value=30)
            mock_redis_cls.return_value = mock_redis

            # Não deve lançar exceção
            await rate_limit_by_api_key(api_key_value="test-key-12345678", settings=settings)

    @pytest.mark.asyncio
    async def test_bloqueia_acima_do_limite_por_api_key(self):
        """Deve lançar HTTPException 429 quando limite por API key é ultrapassado."""
        settings = _make_settings(api_rate_limit_requests=60)

        with patch("app.infrastructure.middleware.rate_limiter.RedisClient") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.increment_with_ttl = AsyncMock(return_value=61)
            mock_redis.get_ttl = AsyncMock(return_value=45)
            mock_redis_cls.return_value = mock_redis

            with pytest.raises(HTTPException) as exc_info:
                await rate_limit_by_api_key(api_key_value="test-key-12345678", settings=settings)

        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_fail_open_por_api_key_quando_redis_indisponivel(self):
        """Deve permitir requisição quando Redis está indisponível (fail-open por API key)."""
        settings = _make_settings()

        with patch("app.infrastructure.middleware.rate_limiter.RedisClient") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.increment_with_ttl = AsyncMock(
                side_effect=Exception("Redis connection error")
            )
            mock_redis_cls.return_value = mock_redis

            # Não deve lançar exceção — fail open
            await rate_limit_by_api_key(api_key_value="test-key-12345678", settings=settings)

    @pytest.mark.asyncio
    async def test_bloqueia_api_key_curta_sem_erro(self):
        """Deve funcionar com API key mais curta que 8 caracteres."""
        settings = _make_settings(api_rate_limit_requests=60)

        with patch("app.infrastructure.middleware.rate_limiter.RedisClient") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.increment_with_ttl = AsyncMock(return_value=61)
            mock_redis.get_ttl = AsyncMock(return_value=30)
            mock_redis_cls.return_value = mock_redis

            with pytest.raises(HTTPException) as exc_info:
                await rate_limit_by_api_key(api_key_value="abc", settings=settings)

        assert exc_info.value.status_code == 429
