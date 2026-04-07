"""Router v1 para o endpoint de consulta de detalhes de URL encurtada.

Versão versionada de url_details_router.py com prefix /urls (sem o /api/).
Montado com prefix /api/v1 no main.py, resultando em /api/v1/urls/{short_code}.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.api_key_auth import api_key_auth
from app.application.dtos.error_response import ErrorResponse
from app.application.dtos.get_url_details_dto import GetUrlDetailsResponse
from app.application.use_cases.get_url_details_use_case import (
    GetUrlDetailsUseCase,
    UrlNotFoundError,
)
from app.config import Settings, get_settings
from app.domain.entities.api_key import ApiKey
from app.infrastructure.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/urls", tags=["URLs"])


async def get_url_details_use_case_dep(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> GetUrlDetailsUseCase:
    """Dependency que delega para container.get_url_details_use_case em runtime."""
    import app.infrastructure.di.container as container  # noqa: PLC0415

    return await container.get_url_details_use_case(session=session, settings=settings)


@router.get(
    "/{short_code}",
    response_model=GetUrlDetailsResponse,
    status_code=200,
    summary="Consultar detalhes de URL encurtada",
    description=(
        "Retorna a URL original, o código curto, a URL completa e a contagem de cliques. "
        "Requer autenticação via header **X-API-Key**."
    ),
    responses={
        200: {
            "description": "Detalhes da URL encontrada.",
            "content": {
                "application/json": {
                    "example": {
                        "original_url": "https://www.exemplo.com/minha-pagina-muito-longa",
                        "short_code": "aB3kZ9",
                        "short_url": "https://short.app/aB3kZ9",
                        "click_count": 42,
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
        404: {
            "model": ErrorResponse,
            "description": "URL encurtada não encontrada.",
            "content": {
                "application/json": {
                    "example": {
                        "status_code": 404,
                        "error_type": "NOT_FOUND",
                        "message": "URL encurtada não encontrada.",
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
async def get_url_details_v1(
    short_code: str,
    use_case: GetUrlDetailsUseCase = Depends(get_url_details_use_case_dep),
    _auth: ApiKey = Depends(api_key_auth),
) -> GetUrlDetailsResponse:
    """Consulta detalhes de uma URL encurtada pelo short_code (v1).

    Retorna a URL original, short_code, URL completa e contagem de cliques.
    Requer autenticação via header X-API-Key.
    """
    try:
        result = await use_case.execute(short_code)
        logger.info(
            "Detalhes de URL consultados via API v1",
            extra={"short_code": short_code, "click_count": result.click_count},
        )
        return result
    except UrlNotFoundError:
        logger.info("URL não encontrada via API v1", extra={"short_code": short_code})
        raise HTTPException(
            status_code=404,
            detail={
                "error_type": "NOT_FOUND",
                "message": "URL encurtada não encontrada.",
            },
        )
