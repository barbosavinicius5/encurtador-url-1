"""Testes unitários para RedisClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.infrastructure.cache.redis_client import RedisClient, get_shared_pool


class TestRedisClient:
    """Testes para RedisClient."""

    def _make_settings(self) -> Settings:
        return Settings(
            redis_url="redis://localhost:6379/0",
            database_url="postgresql+asyncpg://test:test@localhost/test",
        )

    @pytest.mark.asyncio
    async def test_get_retorna_valor_quando_existe(self):
        """get() deve retornar valor quando chave existe no Redis."""
        settings = self._make_settings()
        with patch("app.infrastructure.cache.redis_client.get_shared_pool") as mock_pool:
            mock_pool.return_value = MagicMock()
            with patch("app.infrastructure.cache.redis_client.aioredis.Redis") as mock_redis_cls:
                mock_redis = AsyncMock()
                mock_redis.get = AsyncMock(return_value="https://exemplo.com")
                mock_redis_cls.return_value = mock_redis

                client = RedisClient(settings)
                result = await client.get("url:abc123")

        assert result == "https://exemplo.com"

    @pytest.mark.asyncio
    async def test_get_retorna_none_em_caso_de_erro(self):
        """get() deve retornar None quando Redis lança exceção (fail-safe)."""
        settings = self._make_settings()
        with patch("app.infrastructure.cache.redis_client.get_shared_pool") as mock_pool:
            mock_pool.return_value = MagicMock()
            with patch("app.infrastructure.cache.redis_client.aioredis.Redis") as mock_redis_cls:
                mock_redis = AsyncMock()
                mock_redis.get = AsyncMock(side_effect=Exception("Connection refused"))
                mock_redis_cls.return_value = mock_redis

                client = RedisClient(settings)
                result = await client.get("url:abc123")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_armazena_valor_com_ttl(self):
        """set() deve chamar setex com TTL correto."""
        settings = self._make_settings()
        with patch("app.infrastructure.cache.redis_client.get_shared_pool") as mock_pool:
            mock_pool.return_value = MagicMock()
            with patch("app.infrastructure.cache.redis_client.aioredis.Redis") as mock_redis_cls:
                mock_redis = AsyncMock()
                mock_redis.setex = AsyncMock()
                mock_redis_cls.return_value = mock_redis

                client = RedisClient(settings)
                await client.set("url:abc123", "https://exemplo.com", ttl_seconds=300)

        mock_redis.setex.assert_awaited_once_with("url:abc123", 300, "https://exemplo.com")

    @pytest.mark.asyncio
    async def test_set_silencia_erros(self):
        """set() deve silenciar exceções (fail-safe)."""
        settings = self._make_settings()
        with patch("app.infrastructure.cache.redis_client.get_shared_pool") as mock_pool:
            mock_pool.return_value = MagicMock()
            with patch("app.infrastructure.cache.redis_client.aioredis.Redis") as mock_redis_cls:
                mock_redis = AsyncMock()
                mock_redis.setex = AsyncMock(side_effect=Exception("Connection error"))
                mock_redis_cls.return_value = mock_redis

                client = RedisClient(settings)
                # Não deve lançar exceção
                await client.set("url:abc123", "https://exemplo.com")

    @pytest.mark.asyncio
    async def test_get_ttl_retorna_valor_quando_chave_existe(self):
        """get_ttl() deve retornar TTL da chave."""
        settings = self._make_settings()
        with patch("app.infrastructure.cache.redis_client.get_shared_pool") as mock_pool:
            mock_pool.return_value = MagicMock()
            with patch("app.infrastructure.cache.redis_client.aioredis.Redis") as mock_redis_cls:
                mock_redis = AsyncMock()
                mock_redis.ttl = AsyncMock(return_value=250)
                mock_redis_cls.return_value = mock_redis

                client = RedisClient(settings)
                ttl = await client.get_ttl("url:abc123")

        assert ttl == 250

    @pytest.mark.asyncio
    async def test_get_ttl_retorna_menos_dois_em_caso_de_erro(self):
        """get_ttl() deve retornar -2 quando Redis lança exceção."""
        settings = self._make_settings()
        with patch("app.infrastructure.cache.redis_client.get_shared_pool") as mock_pool:
            mock_pool.return_value = MagicMock()
            with patch("app.infrastructure.cache.redis_client.aioredis.Redis") as mock_redis_cls:
                mock_redis = AsyncMock()
                mock_redis.ttl = AsyncMock(side_effect=Exception("Connection error"))
                mock_redis_cls.return_value = mock_redis

                client = RedisClient(settings)
                ttl = await client.get_ttl("url:abc123")

        assert ttl == -2

    @pytest.mark.asyncio
    async def test_close_nao_faz_nada(self):
        """close() não deve lançar exceção (compatibilidade)."""
        settings = self._make_settings()
        with patch("app.infrastructure.cache.redis_client.get_shared_pool") as mock_pool:
            mock_pool.return_value = MagicMock()
            with patch("app.infrastructure.cache.redis_client.aioredis.Redis") as mock_redis_cls:
                mock_redis_cls.return_value = AsyncMock()
                client = RedisClient(settings)
                # Não deve lançar exceção
                await client.close()
