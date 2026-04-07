"""DTOs para criação de projeto."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    """Request DTO para criação de projeto."""

    name: str = Field(..., min_length=3, max_length=100, description="Nome do projeto")
    description: str | None = Field(None, max_length=500, description="Descrição opcional")


class CreateProjectResponse(BaseModel):
    """Response DTO para projeto criado."""

    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
