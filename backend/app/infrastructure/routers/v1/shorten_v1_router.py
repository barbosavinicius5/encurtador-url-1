"""Router v1 para o endpoint de encurtamento de URL.

Versão versionada de shorten_router.py com path /shorten (sem prefixo /api/).
Montado com prefix /api/v1 no main.py, resultando em /api/v1/shorten.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.api_key_auth import api_key_auth
from app.application.dtos.error_response import ErrorResponse
from app.application.dtos.shorten_url_dto import ShortenUrlRequest, ShortenUrlResponse
from app.application.use_cases.shorten_url_use_case import ShortenUrlUseCase
from app.config import Settings, get_settings
from app.domain.entities.api_key import ApiKey
from app.domain.exceptions import InvalidUrlError, MaliciousDomainError, SlugCollisionError
from app.infrastructure.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter()

SESSION_COOKIE_NAME = "session_id"


async def _get_use_case(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ShortenUrlUseCase:
    """Dependency que delega para container.get_shorten_use_case em runtime."""
    import app.infrastructure.di.container as container  # noqa: PLC0415

    return await container.get_shorten_use_case(session=session, settings=settings)


@router.post(
    "/shorten",
    response_model=ShortenUrlResponse,
    status_code=201,
    summary="Encurtar URL",
    description=(
        "Encurta uma URL longa e retorna o link curto. "
        "Requer autenticação via header **X-API-Key**. "
        "Limite de 60 requisições por minuto por chave de API."
    ),
    responses={
        201: {
            "description": "URL encurtada com sucesso.",
            "content": {
                "application/json": {
                    "example": {
                        "short_code": "aB3kZ9",
                        "short_url": "https://short.app/aB3kZ9",
                        "original_url": "https://www.exemplo.com/pagina-muito-longa",
                    }
                }
            },
        },
        401: {
            "model": ErrorResponse,
            "description": "API key ausente ou inválida.",
            "content": {
                "application/json": {
                    "example": {
                        "status_code": 401,
                        "error_type": "UNAUTHORIZED",
                        "message": "API key ausente ou inválida.",
                    }
                }
            },
        },
        409: {
            "model": ErrorResponse,
            "description": "Slug já em uso ou URL já encurtada nesta sessão.",
            "content": {
                "application/json": {
                    "example": {
                        "status_code": 409,
                        "error_type": "CONFLICT",
                        "message": "Slug já em uso. Tente novamente.",
                    }
                }
            },
        },
        422: {
            "model": ErrorResponse,
            "description": "URL inválida, malformada ou domínio bloqueado.",
            "content": {
                "application/json": {
                    "example": {
                        "status_code": 422,
                        "error_type": "VALIDATION_ERROR",
                        "message": "Campo 'url': URL inválida ou não acessível.",
                    }
                }
            },
        },
        429: {
            "model": ErrorResponse,
            "description": "Rate limit excedido.",
            "content": {
                "application/json": {
                    "example": {
                        "status_code": 429,
                        "error_type": "RATE_LIMIT_EXCEEDED",
                        "message": "Limite de requisições excedido. Tente novamente mais tarde.",
                    }
                }
            },
        },
        500: {
            "model": ErrorResponse,
            "description": "Erro interno do servidor.",
            "content": {
                "application/json": {
                    "example": {
                        "status_code": 500,
                        "error_type": "INTERNAL_ERROR",
                        "message": "Erro interno do servidor.",
                    }
                }
            },
        },
    },
)
async def shorten_url_v1(
    request: ShortenUrlRequest,
    response: Response,
    session_id: Optional[str] = Cookie(default=None),
    use_case: ShortenUrlUseCase = Depends(_get_use_case),
    _auth: ApiKey = Depends(api_key_auth),
) -> ShortenUrlResponse:
    """Encurta uma URL e retorna o link curto (v1).

    Lê o cookie session_id para associar o link à sessão do usuário.
    Se o cookie não existir, gera um novo UUID e o define na resposta.
    """
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

        if is_new_session:
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_id,
                httponly=True,
                samesite="lax",
                path="/",
            )

        return result
    except MaliciousDomainError:
        logger.warning("URL rejeitada por domínio malicioso")
        raise HTTPException(
            status_code=422,
            detail={
                "error_type": "VALIDATION_ERROR",
                "message": "URL contém domínio bloqueado.",
            },
        )
    except InvalidUrlError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error_type": "VALIDATION_ERROR",
                "message": str(e),
            },
        )
    except SlugCollisionError:
        logger.error("Esgotadas tentativas de geração de slug único", exc_info=True)
        raise HTTPException(
            status_code=409,
            detail={
                "error_type": "CONFLICT",
                "message": "Slug já em uso. Tente novamente.",
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error_type": "VALIDATION_ERROR",
                "message": str(e),
            },
        )
    except Exception:
        logger.error("Erro ao encurtar URL", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error_type": "INTERNAL_ERROR",
                "message": "Ocorreu um erro inesperado. Tente novamente mais tarde.",
            },
        )
