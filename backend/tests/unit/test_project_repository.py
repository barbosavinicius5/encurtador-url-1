"""Testes unitários para o PostgreSQLProjectRepository."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities.project import Project
from app.infrastructure.db.repositories.project_repository import PostgreSQLProjectRepository


def _make_project(name="Meu Projeto", description="Desc"):
    return Project.create(
        name=name,
        description=description,
        account_id=uuid4(),
        created_by=uuid4(),
    )


def _make_model(project: Project):
    """Cria um mock de ProjectModel a partir de um Project."""
    model = MagicMock()
    model.id = project.id
    model.account_id = project.account_id
    model.name = project.name.value
    model.description = project.description.value
    model.created_by = project.created_by
    model.is_active = project.is_active
    model.created_at = project.created_at
    return model


class TestPostgreSQLProjectRepository:
    """Testes para o repositório de projetos."""

    async def test_save_returns_project(self):
        session = AsyncMock()
        project = _make_project()
        model = _make_model(project)

        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()

        repo = PostgreSQLProjectRepository(session)

        with patch(
            "app.infrastructure.db.repositories.project_repository.ProjectModel",
            return_value=model,
        ):
            result = await repo.save(project)

        assert result.id == project.id
        assert result.name.value == project.name.value
        session.add.assert_called_once()

    async def test_save_raises_on_duplicate(self):
        session = AsyncMock()
        project = _make_project()
        model = _make_model(project)

        session.add = MagicMock()
        session.flush = AsyncMock(side_effect=IntegrityError("dup", {}, Exception()))
        session.rollback = AsyncMock()

        repo = PostgreSQLProjectRepository(session)

        with patch(
            "app.infrastructure.db.repositories.project_repository.ProjectModel",
            return_value=model,
        ):
            with pytest.raises(ValueError, match="409"):
                await repo.save(project)

        session.rollback.assert_called_once()

    async def test_exists_by_name_and_account_returns_true(self):
        session = AsyncMock()
        account_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid4()
        session.execute = AsyncMock(return_value=mock_result)

        repo = PostgreSQLProjectRepository(session)
        result = await repo.exists_by_name_and_account("Projeto", account_id)

        assert result is True

    async def test_exists_by_name_and_account_returns_false(self):
        session = AsyncMock()
        account_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = PostgreSQLProjectRepository(session)
        result = await repo.exists_by_name_and_account("Inexistente", account_id)

        assert result is False
