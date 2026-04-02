"""Cliente Redis async para cache e rate limiting."""

import logging

import redis.asyncio as aioredis

from app.config import Settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Cliente Redis com métodos de conveniência para cache e rate limiting."""

    def __init__(self, settings: Settings):
        self._client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def get(self, key: str) -> str | None:
        """Recupera um valor do cache pelo key.

        Args:
            key: Chave Redis.

        Returns:
            Valor como string ou None se não existir.
        """
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(
                "Erro ao recuperar do Redis", extra={"key": key, "error": str(e)}
            )
            return None

    async def set(self, key: str, value: str, ttl_seconds: int = 3600) -> None:
        """Armazena um valor no cache com TTL.

        Args:
            key: Chave Redis.
            value: Valor a armazenar.
            ttl_seconds: Tempo de vida em segundos (padrão: 1 hora).
        """
        try:
            await self._client.setex(key, ttl_seconds, value)
        except Exception as e:
            logger.warning(
                "Erro ao armazenar no Redis",
                extra={"key": key, "error": str(e)},
            )

    async def increment_with_ttl(self, key: str, ttl_seconds: int = 60) -> int:
        """Incrementa um contador e define TTL na primeira vez (sliding window simplificado).

        Usa pipeline atômico: INCR + EXPIRE (apenas se TTL não definido).

        Args:
            key: Chave Redis do contador.
            ttl_seconds: Janela de tempo em segundos.

        Returns:
            Valor do contador após incremento.
        """
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds, xx=False)  # Só define TTL se não existir
        results = await pipe.execute()
        return results[0]  # Valor após incremento

    async def close(self) -> None:
        """Fecha a conexão com o Redis."""
        await self._client.aclose()
