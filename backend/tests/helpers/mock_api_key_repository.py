"""Mock do repositório de API Keys para testes unitários."""

from typing import Optional

from app.domain.entities.api_key import ApiKey
from app.domain.ports.api_key_repository_port import ApiKeyRepositoryPort


class MockApiKeyRepository(ApiKeyRepositoryPort):
    """Implementação em memória do ApiKeyRepositoryPort para testes."""

    def __init__(self):
        self._store: dict[str, ApiKey] = {}

    def add_key(self, api_key: ApiKey) -> None:
        """Helper de teste para adicionar uma chave diretamente."""
        self._store[api_key.key] = api_key

    async def get_by_key(self, key: str) -> Optional[ApiKey]:
        """Busca uma API Key pelo valor da chave."""
        return self._store.get(key)

    async def save(self, api_key: ApiKey) -> ApiKey:
        """Persiste uma API Key em memória."""
        self._store[api_key.key] = api_key
        return api_key
