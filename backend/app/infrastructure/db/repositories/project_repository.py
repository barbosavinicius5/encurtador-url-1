"""Adapter PostgreSQL para o repositório de projetos."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.project import Project
from app.domain.ports.project_repository_port import ProjectRepositoryPort
from app.domain.value_objects.project_description import ProjectDescription
from app.domain.value_objects.project_name import ProjectName
from app.infrastructure.db.models import ProjectModel

logger = logging.getLogger(__name__)


class PostgreSQLProjectRepository(ProjectRepositoryPort):
    """Implementação do repositório de projetos usando PostgreSQL via SQLAlchemy async."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, project: Project) -> Project:
        """Persiste um projeto no banco de dados.

        Args:
            project: Entidade a ser persistida.

        Returns:
            Entidade salva.

        Raises:
            ValueError: Se nome duplicado na mesma account (CA-05).
        """
        model = ProjectModel(
            id=project.id,
            account_id=project.account_id,
            name=project.name.value,
            description=project.description.value,
            created_by=project.created_by,
            is_active=project.is_active,
        )
        self.session.add(model)
        try:
            await self.session.flush()
            await self.session.refresh(model)
        except IntegrityError:
            await self.session.rollback()
            raise ValueError("409: Já existe um projeto com esse nome nesta account")

        logger.info("Projeto persistido", extra={"project_id": str(model.id)})

        return Project(
            id=model.id,
            account_id=model.account_id,
            name=ProjectName(model.name),
            description=ProjectDescription(model.description),
            created_by=model.created_by,
            is_active=model.is_active,
            created_at=model.created_at,
        )

    async def exists_by_name_and_account(self, name: str, account_id: UUID) -> bool:
        """Verifica se já existe projeto com esse nome na mesma account.

        Args:
            name: Nome a verificar.
            account_id: UUID da account.

        Returns:
            True se existir, False caso contrário.
        """
        stmt = select(ProjectModel.id).where(
            ProjectModel.name == name,
            ProjectModel.account_id == account_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_by_account(
        self,
        account_id: UUID,
        offset: int = 0,
        limit: int = 20,
        name: str | None = None,
        order_by: str = "created_at",
        order_dir: str = "desc",
        is_active: bool | None = None,
    ) -> tuple[list[Project], int]:
        """Lista projetos de uma account com paginação, filtros e ordenação.

        Args:
            account_id: UUID da account.
            offset: Número de itens a pular.
            limit: Número máximo de itens a retornar.
            name: Filtro parcial por nome (case-insensitive ILIKE).
            order_by: Campo de ordenação ('created_at' ou 'name').
            order_dir: Direção ('asc' ou 'desc').
            is_active: Se None, retorna apenas ativos (CA-03). True/False filtra explicitamente.

        Returns:
            Tupla (lista de projetos, total de projetos que atendem aos filtros).
            Projetos ordenados por created_at DESC por padrão (CA-04).
            Filtra automaticamente soft-deleted quando is_active=None (CA-03).
        """
        # CA-03: por padrão, filtra apenas projetos ativos (soft-delete)
        active_filter = is_active if is_active is not None else True

        filters = [
            ProjectModel.account_id == account_id,
            ProjectModel.is_active.is_(active_filter),
        ]

        # Filtro por nome parcial, case-insensitive (ILIKE)
        if name:
            filters.append(ProjectModel.name.ilike(f"%{name}%"))

        # CA-04: ordenação configurável (padrão: created_at DESC)
        order_col = ProjectModel.created_at if order_by == "created_at" else ProjectModel.name
        order_clause = order_col.desc() if order_dir == "desc" else order_col.asc()

        # Query para contagem total
        count_stmt = select(func.count()).select_from(ProjectModel).where(*filters)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Query para listagem com paginação e ordenação
        list_stmt = (
            select(ProjectModel).where(*filters).order_by(order_clause).offset(offset).limit(limit)
        )
        list_result = await self.session.execute(list_stmt)
        models = list_result.scalars().all()

        projects = [
            Project(
                id=m.id,
                account_id=m.account_id,
                name=ProjectName(m.name),
                description=ProjectDescription(m.description),
                created_by=m.created_by,
                is_active=m.is_active,
                created_at=m.created_at,
            )
            for m in models
        ]

        logger.info(
            "Projetos buscados do banco",
            extra={
                "account_id": str(account_id),
                "total": total,
                "offset": offset,
                "limit": limit,
                "returned": len(projects),
                "filter_name": name,
                "order_by": order_by,
                "order_dir": order_dir,
            },
        )

        return projects, total
