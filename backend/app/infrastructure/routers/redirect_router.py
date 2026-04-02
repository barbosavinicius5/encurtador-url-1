"""Router para o endpoint de redirect de short_code e health check."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.responses import Response

from app.application.use_cases.redirect_url_use_case import RedirectUrlUseCase
from app.infrastructure.di.container import get_redirect_use_case

logger = logging.getLogger(__name__)

router = APIRouter()

# Carregar HTML de erro 404 uma vez no import para evitar I/O em cada request
_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"
_ERROR_404_HTML_PATH = _TEMPLATE_DIR / "404.html"

try:
    _ERROR_404_HTML = _ERROR_404_HTML_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    # Fallback inline caso o arquivo não exista
    _ERROR_404_HTML = (
        "<!DOCTYPE html>"
        '<html lang="pt-BR"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        "<title>Link não encontrado</title></head>"
        '<body><main role="main">'
        "<h1>Link não encontrado</h1>"
        "<p>Este link não existe ou foi removido.</p>"
        "<p>Verifique se o endereço está correto.</p>"
        '<a href="/">Voltar à página inicial</a>'
        "</main></body></html>"
    )


@router.get(
    "/health",
    summary="Health check",
    description="Verifica a disponibilidade da aplicação.",
    tags=["monitoring"],
)
async def health_check() -> dict:
    """Retorna status de disponibilidade da aplicação.

    Returns:
        JSON com status operacional.
    """
    return {"status": "ok"}


@router.get(
    "/{short_code}",
    summary="Redirecionar link curto",
    description="Redireciona um short_code para a URL original.",
    response_class=RedirectResponse,
    status_code=302,
    response_model=None,
)
async def redirect_short_code(
    short_code: str,
    use_case: RedirectUrlUseCase = Depends(get_redirect_use_case),
) -> Response:
    """Redireciona um short_code para a URL original.

    Registra o clique de forma assíncrona (fire-and-forget) via Redis
    sem bloquear a resposta de redirect.

    Args:
        short_code: Identificador único do link encurtado.
        use_case: Use case injetado pelo container de DI.

    Returns:
        Redirect HTTP 302 para a URL original, ou
        HTMLResponse HTTP 404 se o slug não existir.
    """
    try:
        original_url = await use_case.execute(short_code)
        logger.info(
            "Redirect executado",
            extra={"short_code": short_code},
        )
        return RedirectResponse(url=original_url, status_code=302)
    except ValueError:
        logger.info(
            "Slug não encontrado — retornando 404 HTML",
            extra={"short_code": short_code},
        )
        return HTMLResponse(content=_ERROR_404_HTML, status_code=404)
