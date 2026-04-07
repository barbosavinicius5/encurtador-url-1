"""Port (interface) para o repositório de projetos."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.project import Project


class ProjectRepositoryPort(ABC):
    """Interface abstrata para o repositório de projetos."""

    @abstractmethod
    async def save(self, project: Project) -> Project:
        """Persiste um projeto e retorna a entidade salva."""
        ...

    @abstractmethod
    async def exists_by_name_and_account(self, name: str, account_id: UUID) -> bool:
        """Verifica se já existe projeto com esse nome na mesma account."""
        ...

    @abstractmethod
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
            name: Filtro parcial por nome (case-insensitive). None = sem filtro.
            order_by: Campo de ordenação ('created_at' ou 'name').
            order_dir: Direção ('asc' ou 'desc').
            is_active: Se None, retorna apenas ativos (CA-03). True/False filtra explicitamente.

        Returns:
            Tupla (lista de projetos, total de projetos que atendem aos filtros).
        """
        ...
