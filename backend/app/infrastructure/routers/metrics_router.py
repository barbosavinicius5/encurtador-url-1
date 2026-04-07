"""Router para o endpoint de métricas Prometheus."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["monitoring"])


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Métricas Prometheus",
    description=(
        "Expõe métricas de latência e contadores de requisições "
        "no formato Prometheus (text/plain exposition format). "
        "Sem autenticação — público para ferramentas de monitoramento."
    ),
)
async def metrics() -> PlainTextResponse:
    """Retorna métricas da aplicação no formato Prometheus.

    Returns:
        Métricas em texto plano no formato Prometheus exposition format.
    """
    return PlainTextResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
