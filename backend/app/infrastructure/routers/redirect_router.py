"""Router para o endpoint de redirect de short_code."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.application.use_cases.redirect_url_use_case import RedirectUrlUseCase
from app.infrastructure.di.container import get_redirect_use_case

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{short_code}",
    summary="Redirecionar link curto",
    description="Redireciona um short_code para a URL original.",
    response_class=RedirectResponse,
    status_code=301,
)
async def redirect_short_code(
    short_code: str,
    use_case: RedirectUrlUseCase = Depends(get_redirect_use_case),
) -> RedirectResponse:
    """Redireciona um short_code para a URL original.

    Args:
        short_code: Identificador único do link encurtado.
        use_case: Use case injetado pelo container de DI.

    Returns:
        Redirect HTTP 301 para a URL original.

    Raises:
        HTTPException 404: short_code não encontrado.
    """
    try:
        original_url = await use_case.execute(short_code)
        logger.info(
            "Redirect executado",
            extra={"short_code": short_code},
        )
        return RedirectResponse(url=original_url, status_code=301)
    except ValueError:
        raise HTTPException(status_code=404, detail="Link não encontrado")
