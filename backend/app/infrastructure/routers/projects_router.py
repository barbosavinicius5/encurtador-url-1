"""Router para o endpoint de projetos."""

import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.create_project_dto import CreateProjectRequest, CreateProjectResponse
from app.application.dtos.list_projects_dto import ListProjectsRequest, ListProjectsResponse
from app.application.use_cases.create_project_use_case import CreateProjectUseCase
from app.application.use_cases.list_projects_use_case import ListProjectsUseCase
from app.infrastructure.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter()

# account_id fixo para simplificação (sem auth nesta US)
_DEFAULT_ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000001")
_DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000002")


async def _get_use_case(
    session: AsyncSession = Depends(get_session),
) -> CreateProjectUseCase:
    import app.infrastructure.di.container as container  # noqa: PLC0415

    return await container.get_create_project_use_case(session=session)


async def _get_list_use_case(
    session: AsyncSession = Depends(get_session),
) -> ListProjectsUseCase:
    import app.infrastructure.di.container as container  # noqa: PLC0415

    return await container.get_list_projects_use_case(session=session)


@router.post(
    "/projects",
    response_model=CreateProjectResponse,
    status_code=201,
    summary="Criar Projeto",
    description="Cria um novo projeto com nome e descrição.",
    responses={
        201: {"description": "Projeto criado com sucesso"},
        409: {"description": "Nome duplicado na mesma account"},
        422: {"description": "Dados inválidos"},
    },
)
async def create_project(
    request: CreateProjectRequest,
    use_case: CreateProjectUseCase = Depends(_get_use_case),
) -> CreateProjectResponse:
    """Cria um projeto e retorna os dados do projeto criado."""
    try:
        return await use_case.execute(
            request,
            account_id=_DEFAULT_ACCOUNT_ID,
            created_by=_DEFAULT_USER_ID,
        )
    except ValueError as e:
        if "409" in str(e):
            raise HTTPException(
                status_code=409, detail="Já existe um projeto com esse nome nesta account"
            )
        raise HTTPException(status_code=422, detail=str(e))


@router.get(
    "/projects",
    response_model=ListProjectsResponse,
    status_code=200,
    summary="Listar Projetos",
    description=(
        "Lista projetos ativos da account com paginação, filtros e ordenação. "
        "Filtra automaticamente projetos soft-deleted (is_active=False) por padrão. "
        "Ordenados por created_at DESC por padrão (CA-04)."
    ),
    responses={
        200: {"description": "Lista paginada de projetos"},
        422: {"description": "Parâmetros inválidos"},
    },
)
async def list_projects(
    offset: int = Query(0, ge=0, description="Número de itens a pular"),
    limit: int = Query(20, ge=1, le=100, description="Número máximo de itens a retornar"),
    name: str | None = Query(None, description="Filtro parcial por nome (case-insensitive)"),
    order_by: Literal["created_at", "name"] = Query("created_at", description="Campo de ordenação"),
    order_dir: Literal["asc", "desc"] = Query("desc", description="Direção da ordenação"),
    use_case: ListProjectsUseCase = Depends(_get_list_use_case),
) -> ListProjectsResponse:
    """Lista projetos ativos da account com paginação, filtros e ordenação."""
    request = ListProjectsRequest(
        offset=offset,
        limit=limit,
        name=name,
        order_by=order_by,
        order_dir=order_dir,
    )
    return await use_case.execute(request, account_id=_DEFAULT_ACCOUNT_ID)
