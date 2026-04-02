"""Port (interface) para o repositório de URLs."""

from abc import ABC, abstractmethod

from app.domain.entities.shortened_url import ShortenedUrl


class UrlRepositoryPort(ABC):
    """Interface abstrata para o repositório de URLs encurtadas."""

    @abstractmethod
    async def save(self, shortened_url: ShortenedUrl) -> ShortenedUrl:
        """Persiste uma URL encurtada e retorna a entidade com ID."""
        ...

    @abstractmethod
    async def find_by_short_code(self, short_code: str) -> ShortenedUrl | None:
        """Busca uma URL encurtada pelo short_code. Retorna None se não encontrada."""
        ...

    @abstractmethod
    async def exists_by_short_code(self, short_code: str) -> bool:
        """Verifica se um short_code já existe no repositório."""
        ...

    @abstractmethod
    async def increment_click_count(self, short_code: str) -> None:
        """Incrementa o contador de cliques para um short_code."""
        ...
