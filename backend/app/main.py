"""FastAPI application factory."""

import logging
import logging.config

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.application.dtos.error_response import ErrorResponse
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

_logger = logging.getLogger(__name__)

# Mapeamento de status HTTP → error_type semântico
_ERROR_TYPE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMIT_EXCEEDED",
    500: "INTERNAL_ERROR",
}


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
            "\n\n## Erros\n"
            "Todos os erros retornam JSON no formato `ErrorResponse`: "
            "`{status_code, error_type, message}`. "
            "Consulte os schemas em cada endpoint para exemplos concretos."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- Exception Handlers Globais ---
    # Devem ser registrados logo após a criação do app, antes dos middlewares e routers.

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handler global para HTTPException.

        Retorna ErrorResponse padronizado para todos os endpoints de API.
        Exceção especial: GET /{short_code} com Accept: text/html retorna HTML
        para compatibilidade com browsers (redirect_router).
        """
        # Tratamento especial para redirect de browser (HTML)
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header and exc.status_code == 404:
            # O redirect_router já trata esse caso internamente como HTMLResponse.
            # Se chegou ao handler global com texto/html, delegar para HTML.
            from fastapi.responses import HTMLResponse  # noqa: PLC0415

            return HTMLResponse(
                content=(
                    "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'>"
                    "<title>Link não encontrado</title></head><body>"
                    "<h1>Link não encontrado</h1>"
                    "<p>Este link não existe ou foi removido.</p>"
                    "</body></html>"
                ),
                status_code=404,
            )

        # Determinar error_type: preferir do detail estruturado se disponível
        if isinstance(exc.detail, dict) and "error_type" in exc.detail:
            error_type = exc.detail["error_type"]
            message = exc.detail.get("message", "Erro na requisição.")
        else:
            error_type = _ERROR_TYPE_MAP.get(exc.status_code, "HTTP_ERROR")
            message = str(exc.detail) if exc.detail else "Erro na requisição."

        _logger.warning(
            "HTTPException capturada pelo handler global",
            extra={
                "status_code": exc.status_code,
                "error_type": error_type,
                "path": str(request.url.path),
            },
        )

        error = ErrorResponse(
            status_code=exc.status_code,
            error_type=error_type,
            message=message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error.model_dump(),
            headers=dict(exc.headers) if exc.headers else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handler global para erros de validação Pydantic (422).

        Formata os erros de validação em uma mensagem legível e retorna
        ErrorResponse com error_type="VALIDATION_ERROR".
        """
        errors = exc.errors()
        # Construir mensagem legível a partir dos erros de validação
        parts = []
        for e in errors:
            loc = ".".join(str(loc) for loc in e["loc"] if loc != "body")
            msg = e["msg"]
            if loc:
                parts.append(f"Campo '{loc}': {msg}")
            else:
                parts.append(msg)
        message = "; ".join(parts) if parts else "Dados de entrada inválidos."

        _logger.warning(
            "Erro de validação capturado pelo handler global",
            extra={"path": str(request.url.path), "errors_count": len(errors)},
        )

        error = ErrorResponse(
            status_code=422,
            error_type="VALIDATION_ERROR",
            message=message,
        )
        return JSONResponse(status_code=422, content=error.model_dump())

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handler genérico para exceções não tratadas (500).

        Loga a stack trace completa no servidor mas NUNCA a expõe no body
        da resposta HTTP por razões de segurança.
        """
        _logger.exception(
            "Exceção não tratada capturada pelo handler genérico",
            extra={"path": str(request.url.path)},
        )
        error = ErrorResponse(
            status_code=500,
            error_type="INTERNAL_ERROR",
            message="Erro interno do servidor.",
        )
        return JSONResponse(status_code=500, content=error.model_dump())

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
