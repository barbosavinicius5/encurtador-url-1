"""Testes unitários para o ListProjectsUseCase."""

from unittest.mock import AsyncMock
from uuid import uuid4

from app.application.dtos.list_projects_dto import ListProjectsRequest, ListProjectsResponse
from app.application.use_cases.list_projects_use_case import ListProjectsUseCase
from app.domain.entities.project import Project


def _make_project(name: str = "Projeto Teste", is_active: bool = True) -> Project:
    return Project.create(
        name=name,
        description="Descrição",
        account_id=uuid4(),
        created_by=uuid4(),
    )


class TestListProjectsUseCase:
    """Testes unitários para o use case de listagem de projetos."""

    def _make_use_case(self, repository=None) -> ListProjectsUseCase:
        if repository is None:
            repository = AsyncMock()
        return ListProjectsUseCase(repository=repository)

    async def test_list_returns_paginated_response(self):
        """CA-01: GET /projects retorna lista paginada."""
        repository = AsyncMock()
        project = _make_project()
        repository.list_by_account.return_value = ([project], 1)

        use_case = self._make_use_case(repository)
        request = ListProjectsRequest(offset=0, limit=20)
        response = await use_case.execute(request, account_id=uuid4())

        assert isinstance(response, ListProjectsResponse)
        assert len(response.items) == 1
        assert response.total == 1

    async def test_list_supports_offset_and_limit(self):
        """CA-02: Suporta parametros offset e limit."""
        repository = AsyncMock()
        repository.list_by_account.return_value = ([], 0)

        account_id = uuid4()
        use_case = self._make_use_case(repository)
        request = ListProjectsRequest(offset=10, limit=5)
        await use_case.execute(request, account_id=account_id)

        call_kwargs = repository.list_by_account.call_args.kwargs
        assert call_kwargs["account_id"] == account_id
        assert call_kwargs["offset"] == 10
        assert call_kwargs["limit"] == 5

    async def test_list_response_has_offset_and_limit(self):
        """CA-02: Response inclui os parâmetros offset e limit."""
        repository = AsyncMock()
        repository.list_by_account.return_value = ([], 0)

        use_case = self._make_use_case(repository)
        request = ListProjectsRequest(offset=5, limit=10)
        response = await use_case.execute(request, account_id=uuid4())

        assert response.offset == 5
        assert response.limit == 10

    async def test_list_returns_empty_when_no_projects(self):
        """Retorna lista vazia quando não há projetos."""
        repository = AsyncMock()
        repository.list_by_account.return_value = ([], 0)

        use_case = self._make_use_case(repository)
        request = ListProjectsRequest(offset=0, limit=20)
        response = await use_case.execute(request, account_id=uuid4())

        assert response.items == []
        assert response.total == 0

    async def test_list_maps_project_fields_correctly(self):
        """Response items contêm campos corretos do projeto."""
        repository = AsyncMock()
        project = _make_project(name="Projeto Alpha")
        repository.list_by_account.return_value = ([project], 1)

        use_case = self._make_use_case(repository)
        request = ListProjectsRequest(offset=0, limit=20)
        response = await use_case.execute(request, account_id=uuid4())

        item = response.items[0]
        assert item.id == project.id
        assert item.name == "Projeto Alpha"
        assert item.is_active is True
        assert item.created_at is not None

    async def test_list_default_limit_is_20(self):
        """Limite padrão é 20."""
        request = ListProjectsRequest(offset=0)
        assert request.limit == 20

    async def test_list_default_offset_is_zero(self):
        """Offset padrão é 0."""
        request = ListProjectsRequest()
        assert request.offset == 0
