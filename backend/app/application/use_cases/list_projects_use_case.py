"""Use case para listagem de projetos com paginação."""

import logging
from uuid import UUID

from app.application.dtos.list_projects_dto import (
    ListProjectsRequest,
    ListProjectsResponse,
    ProjectItem,
)
from app.domain.ports.project_repository_port import ProjectRepositoryPort

logger = logging.getLogger(__name__)


class ListProjectsUseCase:
    """Use case responsável por listar projetos de uma account com paginação."""

    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self.repository = repository

    async def execute(
        self,
        request: ListProjectsRequest,
        account_id: UUID,
    ) -> ListProjectsResponse:
        """Lista projetos da account com paginação, filtros e ordenação.

        Args:
            request: DTO com parâmetros de paginação, filtros e ordenação.
            account_id: UUID da account dona dos projetos.

        Returns:
            DTO com lista paginada de projetos e metadados de paginação.
            Projetos soft-deleted (is_active=False) são filtrados por padrão (CA-03).
        """
        projects, total = await self.repository.list_by_account(
            account_id=account_id,
            offset=request.offset,
            limit=request.limit,
            name=request.name,
            order_by=request.order_by,
            order_dir=request.order_dir,
            is_active=request.is_active,
        )

        items = [
            ProjectItem(
                id=p.id,
                name=p.name.value,
                description=p.description.value,
                is_active=p.is_active,
                created_at=p.created_at,
            )
            for p in projects
        ]

        logger.info(
            "Projetos listados",
            extra={
                "account_id": str(account_id),
                "total": total,
                "offset": request.offset,
                "limit": request.limit,
                "returned": len(items),
                "filter_name": request.name,
                "order_by": request.order_by,
                "order_dir": request.order_dir,
            },
        )

        return ListProjectsResponse(
            items=items,
            total=total,
            offset=request.offset,
            limit=request.limit,
        )
