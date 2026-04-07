"""Router para o endpoint de listagem de links por sessão."""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Cookie, Depends, Query, Request
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
    "/api/links",
    response_model=LinkListResponse,
    status_code=200,
    summary="Listar links da sessão",
    description=(
        "Retorna todos os links encurtados associados à sessão anônima do usuário. "
        "Suporta ordenação dinâmica por `sort_by` (created_at | click_count) e "
        "`sort_order` (asc | desc)."
    ),
)
async def list_links(
    request: Request,
    session_id: Optional[str] = Cookie(default=None),
    use_case: ListLinksUseCase = Depends(_get_use_case),
    settings: Settings = Depends(get_settings),
    sort_by: Literal["created_at", "click_count"] = Query(
        default="created_at",
        description="Campo de ordenação da lista de links.",
    ),
    sort_order: Literal["asc", "desc"] = Query(
        default="desc",
        description="Direção da ordenação: ascendente (asc) ou descendente (desc).",
    ),
) -> LinkListResponse:
    """Lista todos os links encurtados da sessão atual.

    Args:
        request: Requisição HTTP.
        session_id: Cookie de sessão anônima (lido automaticamente do cookie).
        use_case: Use case injetado pelo container de DI.
        settings: Configurações da aplicação (para construir short_url).
        sort_by: Campo de ordenação. Valores aceitos: 'created_at', 'click_count'.
                 Default: 'created_at'.
        sort_order: Direção da ordenação. Valores aceitos: 'asc', 'desc'. Default: 'desc'.

    Returns:
        Lista de links da sessão com short_code, original_url, short_url e click_count.
    """
    entities = await use_case.execute(
        session_id=session_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )

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
