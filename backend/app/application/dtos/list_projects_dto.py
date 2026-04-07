"""DTOs para listagem de projetos."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ListProjectsRequest(BaseModel):
    """Request DTO para listagem de projetos com paginação, filtros e ordenação."""

    offset: int = Field(0, ge=0, description="Número de itens a pular")
    limit: int = Field(20, ge=1, le=100, description="Número máximo de itens a retornar")
    name: str | None = Field(None, description="Filtro parcial por nome (case-insensitive)")
    order_by: Literal["created_at", "name"] = Field("created_at", description="Campo de ordenação")
    order_dir: Literal["asc", "desc"] = Field("desc", description="Direção da ordenação")
    is_active: bool | None = Field(
        None, description="Filtro por status ativo. None retorna apenas ativos."
    )


class ProjectItem(BaseModel):
    """DTO de um projeto na listagem."""

    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ListProjectsResponse(BaseModel):
    """Response DTO paginado para listagem de projetos."""

    items: list[ProjectItem]
    total: int
    offset: int
    limit: int
