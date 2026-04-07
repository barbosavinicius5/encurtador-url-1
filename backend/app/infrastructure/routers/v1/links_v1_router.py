"""Router v1 para o endpoint de listagem de links por sessão.

Versão versionada de links_router.py com path /links (sem prefixo /api/).
Montado com prefix /api/v1 no main.py, resultando em /api/v1/links.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.link_list_dto import LinkItemResponse, LinkListResponse
from app.application.use_cases.list_links_use_case import ListLinksUseCase
from app.config import Settings, get_settings
from app.infrastructure.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_use_case(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ListLinksUseCase:
    """Dependency que delega para container.get_list_links_use_case em runtime."""
    import app.infrastructure.di.container as container  # noqa: PLC0415

    return await container.get_list_links_use_case(session=session, settings=settings)


@router.get(
    "/links",
    response_model=LinkListResponse,
    status_code=200,
    summary="Listar links da sessão",
    description="Retorna todos os links encurtados associados à sessão anônima do usuário.",
)
async def list_links_v1(
    request: Request,
    session_id: Optional[str] = Cookie(default=None),
    use_case: ListLinksUseCase = Depends(_get_use_case),
    settings: Settings = Depends(get_settings),
) -> LinkListResponse:
    """Lista todos os links encurtados da sessão atual (v1).

    Args:
        request: Requisição HTTP.
        session_id: Cookie de sessão anônima (lido automaticamente do cookie).
        use_case: Use case injetado pelo container de DI.
        settings: Configurações da aplicação (para construir short_url).

    Returns:
        Lista de links da sessão com short_code, original_url, short_url e click_count.
    """
    entities = await use_case.execute(session_id=session_id)

    base_url = settings.base_url.rstrip("/")

    links = [
        LinkItemResponse(
            short_code=entity.short_code,
            original_url=entity.original_url,
            short_url=f"{base_url}/{entity.short_code}",
            click_count=entity.click_count,
            created_at=entity.created_at,
        )
        for entity in entities
    ]

    return LinkListResponse(links=links)
