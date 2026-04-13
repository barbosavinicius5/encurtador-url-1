"""Mock do RedisClient para testes unitários."""

from typing import Optional


class MockRedisClient:
    """Implementação em memória do RedisClient para testes.

    Expõe os mesmos métodos públicos do RedisClient de produção,
    sem realizar qualquer conexão real com Redis.
    """

    def __init__(self):
        self._store: dict[str, str] = {}
        self._ttl: dict[str, Optional[int]] = {}

    async def get(self, key: str) -> Optional[str]:
        """Recupera um valor do cache pelo key."""
        return self._store.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int = 3600) -> None:
        """Armazena um valor no cache com TTL."""
        self._store[key] = value
        self._ttl[key] = ttl_seconds

    async def increment_with_ttl(self, key: str, ttl_seconds: int = 60) -> int:
        """Incrementa um contador e define TTL na primeira vez."""
        current = int(self._store.get(key, "0"))
        new_value = current + 1
        self._store[key] = str(new_value)
        if key not in self._ttl:
            self._ttl[key] = ttl_seconds
        return new_value

    async def delete(self, key: str) -> None:
        """Remove uma chave do cache."""
        self._store.pop(key, None)
        self._ttl.pop(key, None)

    async def close(self) -> None:
        """Fecha a conexão (no-op para mock)."""
        pass
