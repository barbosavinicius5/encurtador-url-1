"""Testes unitários para a entidade Project."""

from uuid import UUID, uuid4

import pytest

from app.domain.entities.project import Project


class TestProjectEntity:
    """Testes para a entidade Project."""

    def test_create_project_with_name_and_description(self):
        account_id = uuid4()
        created_by = uuid4()
        project = Project.create(
            name="Meu Projeto",
            description="Uma descrição",
            account_id=account_id,
            created_by=created_by,
        )
        assert project.name.value == "Meu Projeto"
        assert project.description.value == "Uma descrição"
        assert project.account_id == account_id
        assert project.created_by == created_by

    def test_create_project_without_description(self):
        project = Project.create(
            name="Projeto Sem Desc",
            description=None,
            account_id=uuid4(),
            created_by=uuid4(),
        )
        assert project.description.value is None

    def test_create_project_is_active_by_default(self):
        project = Project.create(
            name="Projeto Ativo",
            description=None,
            account_id=uuid4(),
            created_by=uuid4(),
        )
        assert project.is_active is True

    def test_create_project_generates_uuid(self):
        project = Project.create(
            name="Projeto ID",
            description=None,
            account_id=uuid4(),
            created_by=uuid4(),
        )
        assert isinstance(project.id, UUID)

    def test_create_project_name_too_short_raises(self):
        with pytest.raises(ValueError):
            Project.create(
                name="ab",
                description=None,
                account_id=uuid4(),
                created_by=uuid4(),
            )

    def test_create_project_name_too_long_raises(self):
        with pytest.raises(ValueError):
            Project.create(
                name="a" * 101,
                description=None,
                account_id=uuid4(),
                created_by=uuid4(),
            )

    def test_create_project_description_too_long_raises(self):
        with pytest.raises(ValueError):
            Project.create(
                name="Projeto",
                description="a" * 501,
                account_id=uuid4(),
                created_by=uuid4(),
            )

    def test_create_sets_created_at(self):
        project = Project.create(
            name="Projeto",
            description=None,
            account_id=uuid4(),
            created_by=uuid4(),
        )
        assert project.created_at is not None

    def test_create_requires_account_id(self):
        with pytest.raises((ValueError, TypeError)):
            Project.create(
                name="Projeto",
                description=None,
                account_id=None,  # type: ignore
                created_by=uuid4(),
            )

    def test_create_requires_created_by(self):
        with pytest.raises((ValueError, TypeError)):
            Project.create(
                name="Projeto",
                description=None,
                account_id=uuid4(),
                created_by=None,  # type: ignore
            )
