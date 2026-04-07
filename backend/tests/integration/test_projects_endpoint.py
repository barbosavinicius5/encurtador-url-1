"""Testes de integração para o endpoint POST /projects."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.domain.entities.project import Project


@pytest.fixture
def mock_project():
    return Project.create(
        name="Projeto Teste",
        description="Descrição do projeto",
        account_id=uuid4(),
        created_by=uuid4(),
    )


class TestCreateProjectEndpoint:
    """Testes de integração para POST /projects."""

    async def test_create_project_returns_201(self, client, mock_project):
        with patch(
            "app.infrastructure.di.container.get_create_project_use_case"
        ) as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _project_to_response(mock_project)
            mock_uc_factory.return_value = mock_uc

            response = await client.post(
                "/projects",
                json={"name": "Projeto Teste", "description": "Descrição do projeto"},
            )

        assert response.status_code == 201

    async def test_create_project_response_body(self, client, mock_project):
        with patch(
            "app.infrastructure.di.container.get_create_project_use_case"
        ) as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _project_to_response(mock_project)
            mock_uc_factory.return_value = mock_uc

            response = await client.post(
                "/projects",
                json={"name": "Projeto Teste", "description": "Descrição do projeto"},
            )

        body = response.json()
        assert body["name"] == "Projeto Teste"
        assert body["is_active"] is True
        assert "id" in body

    async def test_create_project_name_too_short_returns_422(self, client):
        response = await client.post(
            "/projects",
            json={"name": "ab", "description": "desc"},
        )
        assert response.status_code == 422

    async def test_create_project_name_too_long_returns_422(self, client):
        response = await client.post(
            "/projects",
            json={"name": "a" * 101, "description": "desc"},
        )
        assert response.status_code == 422

    async def test_create_project_description_too_long_returns_422(self, client):
        response = await client.post(
            "/projects",
            json={"name": "Projeto", "description": "a" * 501},
        )
        assert response.status_code == 422

    async def test_create_project_without_description_returns_201(self, client, mock_project):
        with patch(
            "app.infrastructure.di.container.get_create_project_use_case"
        ) as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _project_to_response(mock_project)
            mock_uc_factory.return_value = mock_uc

            response = await client.post(
                "/projects",
                json={"name": "Projeto Teste"},
            )

        assert response.status_code == 201

    async def test_create_project_duplicate_name_returns_409(self, client):
        with patch(
            "app.infrastructure.di.container.get_create_project_use_case"
        ) as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.side_effect = ValueError("409")
            mock_uc_factory.return_value = mock_uc

            response = await client.post(
                "/projects",
                json={"name": "Duplicado", "description": None},
            )

        assert response.status_code == 409


def _project_to_response(project: Project) -> dict:
    from app.application.dtos.create_project_dto import CreateProjectResponse

    return CreateProjectResponse(
        id=project.id,
        name=project.name.value,
        description=project.description.value,
        is_active=project.is_active,
        created_at=project.created_at,
    )
