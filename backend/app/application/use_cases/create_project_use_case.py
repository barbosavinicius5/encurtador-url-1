"""Use case para criação de projeto."""

import logging
from uuid import UUID

from app.application.dtos.create_project_dto import CreateProjectRequest, CreateProjectResponse
from app.domain.entities.project import Project
from app.domain.ports.project_repository_port import ProjectRepositoryPort

logger = logging.getLogger(__name__)


class CreateProjectUseCase:
    """Use case responsável por criar projetos."""

    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self.repository = repository

    async def execute(
        self,
        request: CreateProjectRequest,
        account_id: UUID,
        created_by: UUID,
    ) -> CreateProjectResponse:
        """Cria um novo projeto.

        Args:
            request: DTO com nome e descrição do projeto.
            account_id: UUID da account dona do projeto.
            created_by: UUID do usuário criador.

        Returns:
            DTO com os dados do projeto criado.

        Raises:
            ValueError: Com mensagem "409" se nome duplicado na mesma account.
            ValueError: Se nome ou descrição inválidos.
        """
        # CA-05: verifica duplicidade de nome na mesma account
        if await self.repository.exists_by_name_and_account(request.name, account_id):
            raise ValueError("409: Já existe um projeto com esse nome nesta account")

        # Cria entidade via factory (CA-02, CA-03, CA-04)
        project = Project.create(
            name=request.name,
            description=request.description,
            account_id=account_id,
            created_by=created_by,
        )

        saved = await self.repository.save(project)

        logger.info(
            "Projeto criado", extra={"project_id": str(saved.id), "project_name": saved.name.value}
        )

        return CreateProjectResponse(
            id=saved.id,
            name=saved.name.value,
            description=saved.description.value,
            is_active=saved.is_active,
            created_at=saved.created_at,
        )
