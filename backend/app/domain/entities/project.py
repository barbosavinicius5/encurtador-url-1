"""Entidade de domínio Project."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.value_objects.project_description import ProjectDescription
from app.domain.value_objects.project_name import ProjectName


@dataclass
class Project:
    """Entidade que representa um Projeto."""

    id: UUID
    account_id: UUID
    name: ProjectName
    description: ProjectDescription
    created_by: UUID
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        name: str,
        description: str | None,
        account_id: UUID,
        created_by: UUID,
    ) -> "Project":
        """Factory method para criar um novo projeto com validações.

        Args:
            name: Nome do projeto (3-100 chars).
            description: Descrição opcional (máx 500 chars).
            account_id: UUID da account dona do projeto.
            created_by: UUID do usuário que criou.

        Returns:
            Nova instância de Project com status ativo.

        Raises:
            ValueError: Se account_id ou created_by forem None, ou se name/description inválidos.
        """
        if account_id is None:
            raise ValueError("account_id é obrigatório")
        if created_by is None:
            raise ValueError("created_by é obrigatório")

        return cls(
            id=uuid4(),
            account_id=account_id,
            name=ProjectName(name),
            description=ProjectDescription(description),
            created_by=created_by,
            is_active=True,
        )
