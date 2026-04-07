"""FastAPI application factory."""

import logging
import logging.config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from app.config import get_settings
from app.core.logging_config import LOGGING_CONFIG
from app.infrastructure.middleware.metrics_middleware import MetricsMiddleware
from app.infrastructure.middleware.request_id_middleware import RequestIdMiddleware
from app.infrastructure.routers.links_router import router as links_router
from app.infrastructure.routers.metrics_router import router as metrics_router
from app.infrastructure.routers.redirect_router import router as redirect_router
from app.infrastructure.routers.shorten_router import router as shorten_router
from app.infrastructure.routers.url_details_router import router as url_details_router


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
            "- `GET /{short_code}` — Redirecionar para a URL original\n"
            "- `GET /metrics` — Métricas Prometheus (latência e contadores)"
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

    # Middlewares de observabilidade
    # Ordem: RequestIdMiddleware deve ser adicionado ANTES de MetricsMiddleware
    # para garantir que o request_id esteja disponível durante a captura de métricas.
    # Nota: add_middleware aplica em ordem reversa (LIFO), então o último adicionado
    # é o primeiro a executar.
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # Routers — ordem importa: shorten e links antes de redirect para evitar conflito
    app.include_router(metrics_router)
    app.include_router(shorten_router)
    app.include_router(links_router)
    app.include_router(url_details_router)
    app.include_router(redirect_router)

    return app


app = create_app()
