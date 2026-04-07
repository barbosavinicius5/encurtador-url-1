"""Router de compatibilidade retroativa com redirects HTTP 301.

Redireciona as rotas legadas /api/... para os novos paths versionados /api/v1/...
Garante que integrações existentes não quebrem durante a transição.

Política de versionamento: ver VERSIONING_POLICY.md na raiz do repositório.
"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["legacy"])


@router.post("/api/shorten", include_in_schema=False)
async def legacy_shorten() -> RedirectResponse:
    """Redireciona POST /api/shorten para /api/v1/shorten (HTTP 301)."""
    return RedirectResponse(url="/api/v1/shorten", status_code=301)


@router.get("/api/links", include_in_schema=False)
async def legacy_links() -> RedirectResponse:
    """Redireciona GET /api/links para /api/v1/links (HTTP 301)."""
    return RedirectResponse(url="/api/v1/links", status_code=301)


@router.get("/api/urls/{short_code}", include_in_schema=False)
async def legacy_urls(short_code: str) -> RedirectResponse:
    """Redireciona GET /api/urls/{short_code} para /api/v1/urls/{short_code} (HTTP 301)."""
    return RedirectResponse(url=f"/api/v1/urls/{short_code}", status_code=301)
