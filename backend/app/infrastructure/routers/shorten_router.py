"""Router para o endpoint de encurtamento de URL."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.shorten_url_dto import ShortenUrlRequest, ShortenUrlResponse
from app.application.use_cases.shorten_url_use_case import ShortenUrlUseCase
from app.config import Settings, get_settings
from app.infrastructure.db.session import get_session
from app.infrastructure.middleware.rate_limiter import rate_limit_by_ip

logger = logging.getLogger(__name__)

router = APIRouter()

SESSION_COOKIE_NAME = "session_id"


async def _get_use_case(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ShortenUrlUseCase:
    """Dependency que delega para container.get_shorten_use_case em runtime.

    Ao importar `container` dentro da função (não no topo do módulo),
    o unittest.mock.patch em `app.infrastructure.di.container.get_shorten_use_case`
    é capturado corretamente.
    """
    import app.infrastructure.di.container as container  # noqa: PLC0415

    return await container.get_shorten_use_case(session=session, settings=settings)


@router.post(
    "/api/shorten",
    response_model=ShortenUrlResponse,
    status_code=201,
    summary="Encurtar URL",
    description="Encurta uma URL longa e retorna o link curto.",
    dependencies=[Depends(rate_limit_by_ip)],
)
async def shorten_url(
    request: ShortenUrlRequest,
    response: Response,
    session_id: Optional[str] = Cookie(default=None),
    use_case: ShortenUrlUseCase = Depends(_get_use_case),
) -> ShortenUrlResponse:
    """Encurta uma URL e retorna o link curto.

    Lê o cookie session_id para associar o link à sessão do usuário.
    Se o cookie não existir, gera um novo UUID e o define na resposta.
    """
    # Gerenciar sessão anônima via cookie
    is_new_session = False
    if not session_id:
        session_id = str(uuid.uuid4())
        is_new_session = True
        logger.info("Nova sessão anônima criada", extra={"session_id_prefix": session_id[:8]})

    try:
        result = await use_case.execute(request, session_id=session_id)
        logger.info(
            "URL encurtada com sucesso",
            extra={"short_code": result.short_code},
        )

        # Setar cookie apenas quando é uma nova sessão
        if is_new_session:
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_id,
                httponly=True,
                samesite="lax",
                path="/",
            )

        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        logger.error("Erro interno ao encurtar URL", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Erro interno ao processar requisição")
