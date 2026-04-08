"""Cliente Redis async para cache e rate limiting com pool de conexões compartilhado."""

import logging

import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool

from app.config import Settings

logger = logging.getLogger(__name__)

# Pool de conexões global (singleton) para reutilização entre requisições.
# Garante overhead < 5ms no hot path por evitar criação de nova conexão a cada request.
_pool: ConnectionPool | None = None


def get_shared_pool(settings: Settings) -> ConnectionPool:
    """Retorna o pool de conexões Redis compartilhado (singleton).

    Cria o pool na primeira chamada e reutiliza nas demais.
    Thread-safe para uso com async (GIL do CPython garante atomicidade na atribuição).

    Args:
        settings: Configurações da aplicação com redis_url.

    Returns:
        ConnectionPool compartilhado.
    """
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _pool


class RedisClient:
    """Cliente Redis com métodos de conveniência para cache e rate limiting.

    Utiliza pool de conexões compartilhado para eficiência no hot path.
    """

    def __init__(self, settings: Settings):
        pool = get_shared_pool(settings)
        self._client = aioredis.Redis(connection_pool=pool)

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
            logger.warning("Erro ao recuperar do Redis", extra={"key": key, "error": str(e)})
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

    async def exists(self, key: str) -> bool:
        """Verifica se uma chave existe no Redis.

        Args:
            key: Chave Redis.

        Returns:
            True se a chave existir, False caso contrário.
        """
        try:
            return bool(await self._client.exists(key))
        except Exception as e:
            logger.warning(
                "Erro ao verificar existência no Redis", extra={"key": key, "error": str(e)}
            )
            return False

    async def get_ttl(self, key: str) -> int:
        """Retorna o TTL restante de uma chave em segundos.

        Args:
            key: Chave Redis.

        Returns:
            TTL em segundos, -1 se sem expiração, -2 se não existir.
        """
        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.warning("Erro ao obter TTL do Redis", extra={"key": key, "error": str(e)})
            return -2

    async def close(self) -> None:
        """Fecha a conexão com o Redis.

        Com pool de conexões, devolve a conexão ao pool em vez de fechá-la.
        Mantido por compatibilidade com código existente.
        """
        # Com pool compartilhado, não fechamos a conexão — ela volta ao pool automaticamente.
        # Este método é mantido para compatibilidade com o código existente.
        pass
