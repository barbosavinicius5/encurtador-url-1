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
from app.infrastructure.routers.legacy_compat_router import router as legacy_compat_router
from app.infrastructure.routers.metrics_router import router as metrics_router
from app.infrastructure.routers.redirect_router import router as redirect_router
from app.infrastructure.routers.v1.links_v1_router import router as links_v1_router
from app.infrastructure.routers.v1.shorten_v1_router import router as shorten_v1_router
from app.infrastructure.routers.v1.url_details_v1_router import router as url_details_v1_router


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI.

    Returns:
        Instância configurada do FastAPI.
    """
    logging.config.dictConfig(LOGGING_CONFIG)

    settings = get_settings()

    app = FastAPI(
        title="Encurtador de URL API v1",
        description=(
            "API REST para encurtamento de URLs com redirect, rastreamento de cliques e rate limiting. "
            "Todos os endpoints REST estão disponíveis sob `/api/v1/`. "
            "Os paths legados `/api/*` emitem redirect HTTP 301 para `/api/v1/*`."
            "\n\n## Autenticação\n"
            "Os endpoints `/api/v1/shorten` e `/api/v1/urls/{short_code}` requerem autenticação "
            "via header **X-API-Key**."
            "\n\n## Rate Limiting\n"
            "Limite de **60 requisições por minuto** por API Key. "
            "Ao ultrapassar, a resposta retorna HTTP 429 com header `Retry-After`."
            "\n\n## Endpoints Principais\n"
            "- `POST /api/v1/shorten` — Encurtar uma URL\n"
            "- `GET /api/v1/urls/{short_code}` — Consultar detalhes e cliques\n"
            "- `GET /api/v1/links` — Listar links da sessão\n"
            "- `GET /{short_code}` — Redirecionar para a URL original\n"
            "- `GET /metrics` — Métricas Prometheus (latência e contadores)"
            "\n\n## Versionamento\n"
            "Consulte `VERSIONING_POLICY.md` para entender quando uma nova versão da API é necessária."
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

    # Endpoints de API REST versionados sob /api/v1/
    app.include_router(shorten_v1_router, prefix="/api/v1", tags=["shorten"])
    app.include_router(links_v1_router, prefix="/api/v1", tags=["links"])
    app.include_router(url_details_v1_router, prefix="/api/v1")

    # Métricas e redirect de browser — fora do versionamento
    app.include_router(metrics_router)
    app.include_router(redirect_router)

    # Compatibilidade retroativa — rotas legadas com redirect HTTP 301
    # include_in_schema=False para não poluir o /docs com rotas deprecated
    app.include_router(legacy_compat_router, include_in_schema=False)

    return app


app = create_app()
