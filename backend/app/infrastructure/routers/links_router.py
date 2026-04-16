"""Router para o endpoint de listagem de links por sessão."""

import logging
import re
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.link_list_dto import LinkItemResponse, LinkListResponse
from app.application.use_cases.list_links_use_case import ListLinksUseCase
from app.config import Settings, get_settings
from app.infrastructure.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter()

# Regex para validar UUID v4
_UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Headers de segurança padrão para todas as respostas do endpoint
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Type": "application/json",
}


def _is_valid_session_id(value: Optional[str]) -> bool:
    """Valida se o session_id tem formato UUID v4 válido.

    Args:
        value: String a validar.

    Returns:
        True se for UUID v4 válido, False caso contrário.
    """
    if not value or not value.strip():
        return False
    return bool(_UUID_V4_PATTERN.match(value.strip()))


async def _get_use_case(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ListLinksUseCase:
    """Dependency que delega para container.get_list_links_use_case em runtime."""
    import app.infrastructure.di.container as container  # noqa: PLC0415

    return await container.get_list_links_use_case(session=session, settings=settings)


def _sanitize_original_url(url: str) -> str:
    """Sanitiza original_url, retornando string vazia para URLs malformadas ou perigosas.

    Aceita apenas URLs absolutas com scheme http ou https.
    Esquemas como javascript:, data:, vbscript: ou URLs relativas são sanitizados.

    Args:
        url: URL original a sanitizar.

    Returns:
        URL original se válida, string vazia caso contrário.
    """
    from urllib.parse import urlparse  # noqa: PLC0415

    if not url or not url.strip():
        return ""
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            return ""
        return url
    except Exception:
        return ""


@router.get(
    "/api/links",
    response_model=None,
    status_code=200,
    summary="Listar links da sessão",
    description="Retorna todos os links encurtados associados à sessão anônima do usuário.",
)
async def list_links(
    request: Request,
    session_id: Optional[str] = Cookie(default=None),
    x_session_id: Optional[str] = Header(default=None),
    use_case: ListLinksUseCase = Depends(_get_use_case),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Lista todos os links encurtados da sessão atual.

    Valida o session_id (cookie ou header X-Session-Id), executa o use case
    e aplica sanitização de URLs na resposta. Retorna headers de segurança
    em todas as respostas (200, 400, 500).

    Args:
        request: Requisição HTTP.
        session_id: Cookie de sessão anônima.
        x_session_id: Header X-Session-Id alternativo ao cookie.
        use_case: Use case injetado pelo container de DI.
        settings: Configurações da aplicação (para construir short_url).

    Returns:
        JSONResponse com lista de links ou mensagem de erro.
    """
    # Resolução do session_id: cookie tem prioridade, depois header X-Session-Id
    resolved_session_id = session_id or x_session_id

    # Validação de formato do session_id (UUID v4)
    if not _is_valid_session_id(resolved_session_id):
        logger.warning(
            "Requisição rejeitada: session_id ausente ou formato inválido",
            extra={"path": "/api/links"},
        )
        return JSONResponse(
            status_code=400,
            content={"error": "session_id ausente ou com formato inválido"},
            headers=_SECURITY_HEADERS,
        )

    try:
        entities = await use_case.execute(session_id=resolved_session_id)
    except Exception as exc:
        # Registrar exceção em log sem expor detalhes ao cliente
        logger.error(
            "Erro interno ao listar links",
            extra={
                "session_id_prefix": resolved_session_id[:8] if resolved_session_id else "",
                "exception_type": type(exc).__name__,
            },
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Erro interno ao processar a requisição"},
            headers=_SECURITY_HEADERS,
        )

    base_url = settings.base_url.rstrip("/")

    links = [
        LinkItemResponse(
            short_code=entity.short_code,
            original_url=_sanitize_original_url(entity.original_url),
            short_url=f"{base_url}/{entity.short_code}",
            click_count=entity.click_count,
            created_at=entity.created_at,
        )
        for entity in entities
    ]

    response_data = LinkListResponse(links=links)

    return JSONResponse(
        status_code=200,
        content=response_data.model_dump(mode="json"),
        headers=_SECURITY_HEADERS,
    )
