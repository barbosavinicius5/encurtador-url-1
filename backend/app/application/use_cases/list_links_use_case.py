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

    async def execute(
        self,
        session_id: Optional[str],
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[ShortenedUrl]:
        """Retorna todos os links associados ao session_id.

        Args:
            session_id: UUID da sessão anônima. Se None ou vazio, retorna lista vazia.
            sort_by: Campo de ordenação. Valores aceitos: 'created_at', 'click_count'.
                     Default: 'created_at'.
            sort_order: Direção da ordenação. Valores aceitos: 'asc', 'desc'.
                        Default: 'desc'.

        Returns:
            Lista de entidades ShortenedUrl ordenadas conforme os parâmetros.
        """
        if not session_id:
            logger.info("Listagem de links solicitada sem session_id — retornando lista vazia")
            return []

        links = await self.repository.find_by_session_id(
            session_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        logger.info(
            "Links listados por sessão",
            extra={
                "session_id_prefix": session_id[:8] if len(session_id) >= 8 else session_id,
                "count": len(links),
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )
        return links
