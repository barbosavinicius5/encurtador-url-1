"""Testes unitários para o CreateProjectUseCase."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.dtos.create_project_dto import CreateProjectRequest, CreateProjectResponse
from app.application.use_cases.create_project_use_case import CreateProjectUseCase
from app.domain.entities.project import Project


class TestCreateProjectUseCase:
    """Testes para o use case de criação de projeto."""

    def _make_use_case(self, repository=None):
        if repository is None:
            repository = AsyncMock()
        return CreateProjectUseCase(repository=repository)

    def _make_saved_project(self, name="Meu Projeto", description="Desc"):
        project = Project.create(
            name=name,
            description=description,
            account_id=uuid4(),
            created_by=uuid4(),
        )
        return project

    async def test_create_project_returns_response(self):
        repository = AsyncMock()
        saved = self._make_saved_project()
        repository.save.return_value = saved
        repository.exists_by_name_and_account.return_value = False

        use_case = self._make_use_case(repository)
        request = CreateProjectRequest(name="Meu Projeto", description="Desc")
        response = await use_case.execute(
            request, account_id=saved.account_id, created_by=saved.created_by
        )

        assert isinstance(response, CreateProjectResponse)
        assert response.name == "Meu Projeto"
        assert response.is_active is True

    async def test_create_project_calls_save(self):
        repository = AsyncMock()
        saved = self._make_saved_project()
        repository.save.return_value = saved
        repository.exists_by_name_and_account.return_value = False

        use_case = self._make_use_case(repository)
        request = CreateProjectRequest(name="Meu Projeto", description="Desc")
        await use_case.execute(request, account_id=saved.account_id, created_by=saved.created_by)

        repository.save.assert_called_once()

    async def test_create_project_duplicate_name_raises_409(self):
        repository = AsyncMock()
        repository.exists_by_name_and_account.return_value = True

        use_case = self._make_use_case(repository)
        request = CreateProjectRequest(name="Duplicado", description=None)

        with pytest.raises(ValueError, match="409"):
            await use_case.execute(request, account_id=uuid4(), created_by=uuid4())

    async def test_create_project_without_description(self):
        repository = AsyncMock()
        saved = self._make_saved_project(description=None)
        repository.save.return_value = saved
        repository.exists_by_name_and_account.return_value = False

        use_case = self._make_use_case(repository)
        request = CreateProjectRequest(name="Projeto", description=None)
        response = await use_case.execute(
            request, account_id=saved.account_id, created_by=saved.created_by
        )

        assert response.description is None or response.description == ""

    async def test_create_project_invalid_name_raises(self):
        """Pydantic valida min_length=3 no DTO antes de chegar ao use case."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CreateProjectRequest(name="ab", description=None)
