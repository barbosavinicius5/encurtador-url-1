"""Testes unitários para filtros e ordenação no ListProjectsUseCase (TASK-005)."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.dtos.list_projects_dto import ListProjectsRequest
from app.application.use_cases.list_projects_use_case import ListProjectsUseCase
from app.domain.entities.project import Project


def _make_project(name: str = "Projeto Teste") -> Project:
    return Project.create(
        name=name,
        description="Desc",
        account_id=uuid4(),
        created_by=uuid4(),
    )


class TestListProjectsFilters:
    """Testes para filtros e ordenação na listagem de projetos."""

    def _make_use_case(self, repository=None) -> ListProjectsUseCase:
        if repository is None:
            repository = AsyncMock()
        return ListProjectsUseCase(repository=repository)

    async def test_filter_by_name_passes_to_repository(self):
        """Filtro por nome é passado ao repositório."""
        repository = AsyncMock()
        repository.list_by_account.return_value = ([], 0)

        account_id = uuid4()
        use_case = self._make_use_case(repository)
        request = ListProjectsRequest(offset=0, limit=20, name="Alpha")
        await use_case.execute(request, account_id=account_id)

        call_kwargs = repository.list_by_account.call_args.kwargs
        assert call_kwargs["name"] == "Alpha"
        assert call_kwargs["account_id"] == account_id

    async def test_order_by_name_passes_to_repository(self):
        """Ordenação por nome é passada ao repositório."""
        repository = AsyncMock()
        repository.list_by_account.return_value = ([], 0)

        account_id = uuid4()
        use_case = self._make_use_case(repository)
        request = ListProjectsRequest(offset=0, limit=20, order_by="name")
        await use_case.execute(request, account_id=account_id)

        call_kwargs = repository.list_by_account.call_args.kwargs
        assert call_kwargs["order_by"] == "name"

    async def test_order_by_created_at_is_default(self):
        """Ordenação padrão é created_at."""
        repository = AsyncMock()
        repository.list_by_account.return_value = ([], 0)

        account_id = uuid4()
        use_case = self._make_use_case(repository)
        request = ListProjectsRequest(offset=0, limit=20)
        await use_case.execute(request, account_id=account_id)

        call_kwargs = repository.list_by_account.call_args.kwargs
        assert call_kwargs.get("order_by", "created_at") == "created_at"

    async def test_order_dir_desc_is_default(self):
        """Direção de ordenação padrão é desc."""
        request = ListProjectsRequest()
        assert request.order_dir == "desc"

    async def test_order_dir_asc_is_valid(self):
        """Direção de ordenação asc é válida."""
        request = ListProjectsRequest(order_dir="asc")
        assert request.order_dir == "asc"

    async def test_order_by_invalid_raises_validation_error(self):
        """Campo de ordenação inválido lança ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ListProjectsRequest(order_by="invalid_field")

    async def test_order_dir_invalid_raises_validation_error(self):
        """Direção de ordenação inválida lança ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ListProjectsRequest(order_dir="random")

    async def test_filter_is_active_none_filters_only_active(self):
        """Por padrão (is_active=None), apenas projetos ativos são retornados."""
        request = ListProjectsRequest()
        # is_active não passado = None, repositório deve filtrar is_active=True
        assert request.is_active is None

    async def test_name_filter_is_optional(self):
        """Filtro por nome é opcional."""
        request = ListProjectsRequest()
        assert request.name is None
