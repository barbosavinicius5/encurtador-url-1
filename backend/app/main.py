"""FastAPI application factory."""

import logging
import logging.config

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.infrastructure.routers.links_router import router as links_router
from app.infrastructure.routers.redirect_router import router as redirect_router
from app.infrastructure.routers.shorten_router import router as shorten_router
from app.infrastructure.routers.url_details_router import router as url_details_router

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI.

    Returns:
        Instância configurada do FastAPI.
    """
    logging.config.dictConfig(LOGGING_CONFIG)

    settings = get_settings()

    app = FastAPI(
        title="Encurtador de URL",
        description=(
            "API REST para encurtamento de URLs com redirect, rastreamento de cliques e rate limiting. "
            "\n\n## Autenticação\n"
            "Os endpoints `/api/shorten` e `/api/urls/{short_code}` requerem autenticação via header **X-API-Key**."
            "\n\n## Rate Limiting\n"
            "Limite de **60 requisições por minuto** por API Key. "
            "Ao ultrapassar, a resposta retorna HTTP 429 com header `Retry-After`."
            "\n\n## Endpoints Principais\n"
            "- `POST /api/shorten` — Encurtar uma URL\n"
            "- `GET /api/urls/{short_code}` — Consultar detalhes e cliques\n"
            "- `GET /{short_code}` — Redirecionar para a URL original"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # HTTPS redirect middleware — apenas em produção
    # Em desenvolvimento e testes, o middleware é desativado para não interferir
    if settings.environment == "production":
        app.add_middleware(HTTPSRedirectMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers — ordem importa: shorten e links antes de redirect para evitar conflito
    app.include_router(shorten_router)
    app.include_router(links_router)
    app.include_router(url_details_router)
    app.include_router(redirect_router)

    # Handler global de exceções — registrado APÓS os routers e handlers específicos
    # Captura qualquer exceção não tratada que não seja HTTPException
    # Garante que nenhum detalhe técnico vaze na resposta
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handler global que captura exceções não tratadas e retorna resposta padronizada.

        Registra o erro internamente (com stack trace) sem expô-lo ao cliente.
        HTTPExceptions são tratadas pelo handler padrão do FastAPI e não chegam aqui.
        """
        logger = logging.getLogger(__name__)
        logger.error(
            "Exceção não tratada capturada pelo handler global",
            exc_info=exc,
            extra={"path": str(request.url), "method": request.method},
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Ocorreu um erro inesperado. Tente novamente mais tarde."},
        )

    return app


app = create_app()
