"""Use case para listagem de links por sessão."""

import logging
from typing import Optional

from app.domain.entities.shortened_url import ShortenedUrl
from app.domain.ports.url_repository_port import UrlRepositoryPort

logger = logging.getLogger(__name__)


class ListLinksUseCase:
    """Use case responsável por listar links da sessão do usuário."""

    def __init__(self, repository: UrlRepositoryPort):
        self.repository = repository

    async def execute(self, session_id: Optional[str]) -> list[ShortenedUrl]:
        """Retorna todos os links associados ao session_id.

        Args:
            session_id: UUID da sessão anônima. Se None ou vazio, retorna lista vazia.

        Returns:
            Lista de entidades ShortenedUrl ordenadas por created_at DESC.
        """
        if not session_id:
            logger.info("Listagem de links solicitada sem session_id — retornando lista vazia")
            return []

        links = await self.repository.find_by_session_id(session_id)
        logger.info(
            "Links listados por sessão",
            extra={
                "session_id_prefix": session_id[:8] if len(session_id) >= 8 else session_id,
                "count": len(links),
            },
        )
        return links
