"""Port (interface) para o repositório de API Keys."""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.api_key import ApiKey


class ApiKeyRepositoryPort(ABC):
    """Interface abstrata para o repositório de API Keys."""

    @abstractmethod
    async def get_by_key(self, key: str) -> Optional[ApiKey]:
        """Busca uma API Key pelo valor da chave.

        Args:
            key: Valor da chave de API.

        Returns:
            Entidade ApiKey se encontrada e ativa, None caso contrário.
        """
        ...

    @abstractmethod
    async def save(self, api_key: ApiKey) -> ApiKey:
        """Persiste uma API Key no repositório.

        Args:
            api_key: Entidade a ser persistida.

        Returns:
            Entidade com ID gerado.
        """
        ...
