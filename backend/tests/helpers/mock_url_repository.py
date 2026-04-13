"""Mock do repositório de URLs para testes unitários."""

from typing import Optional

from app.domain.entities.shortened_url import ShortenedUrl
from app.domain.ports.url_repository_port import UrlRepositoryPort


class MockUrlRepository(UrlRepositoryPort):
    """Implementação em memória do UrlRepositoryPort para testes."""

    def __init__(self):
        self._store: dict[str, ShortenedUrl] = {}
        self._next_id: int = 1

    async def save(self, shortened_url: ShortenedUrl) -> ShortenedUrl:
        """Persiste uma URL encurtada em memória."""
        if shortened_url.id is None:
            shortened_url.id = self._next_id
            self._next_id += 1
        self._store[shortened_url.short_code] = shortened_url
        return shortened_url

    async def find_by_short_code(self, short_code: str) -> Optional[ShortenedUrl]:
        """Busca uma URL encurtada pelo short_code."""
        return self._store.get(short_code)

    async def exists_by_short_code(self, short_code: str) -> bool:
        """Verifica se um short_code já existe."""
        return short_code in self._store

    async def increment_click_count(self, short_code: str) -> None:
        """Incrementa o contador de cliques."""
        if short_code in self._store:
            entity = self._store[short_code]
            self._store[short_code] = ShortenedUrl(
                id=entity.id,
                original_url=entity.original_url,
                short_code=entity.short_code,
                created_at=entity.created_at,
                click_count=entity.click_count + 1,
                deleted_at=entity.deleted_at,
                session_id=entity.session_id,
            )

    async def find_by_session_id(self, session_id: str) -> list[ShortenedUrl]:
        """Retorna todos os links associados ao session_id."""
        if not session_id:
            return []
        return [url for url in self._store.values() if url.session_id == session_id]
