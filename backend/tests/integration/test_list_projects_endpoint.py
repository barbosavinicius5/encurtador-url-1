"""Testes de integração para o endpoint GET /projects."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.domain.entities.project import Project


def _make_project(name: str = "Projeto Teste", is_active: bool = True) -> Project:
    return Project.create(
        name=name,
        description="Descrição do projeto",
        account_id=uuid4(),
        created_by=uuid4(),
    )


def _project_to_item(project: Project) -> dict:
    from app.application.dtos.list_projects_dto import ProjectItem

    return ProjectItem(
        id=project.id,
        name=project.name.value,
        description=project.description.value,
        is_active=project.is_active,
        created_at=project.created_at,
    )


class TestListProjectsEndpoint:
    """Testes de integração para GET /projects."""

    async def test_list_projects_returns_200(self, client):
        """CA-01: GET /projects retorna 200."""
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([])
            mock_uc_factory.return_value = mock_uc

            response = await client.get("/projects")

        assert response.status_code == 200

    async def test_list_projects_response_structure(self, client):
        """CA-01: Response tem estrutura paginada com items, total, offset, limit."""
        project = _make_project()
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([project], total=1)
            mock_uc_factory.return_value = mock_uc

            response = await client.get("/projects")

        body = response.json()
        assert "items" in body
        assert "total" in body
        assert "offset" in body
        assert "limit" in body

    async def test_list_projects_with_offset_and_limit(self, client):
        """CA-02: Suporta parâmetros offset e limit."""
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([], offset=10, limit=5)
            mock_uc_factory.return_value = mock_uc

            response = await client.get("/projects?offset=10&limit=5")

        assert response.status_code == 200
        body = response.json()
        assert body["offset"] == 10
        assert body["limit"] == 5

    async def test_list_projects_default_pagination(self, client):
        """CA-02: Usa offset=0 e limit=20 por padrão."""
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([])
            mock_uc_factory.return_value = mock_uc

            response = await client.get("/projects")

        assert response.status_code == 200
        body = response.json()
        assert body["offset"] == 0
        assert body["limit"] == 20

    async def test_list_projects_item_fields(self, client):
        """Response items contêm campos corretos."""
        project = _make_project("Projeto Alpha")
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([project], total=1)
            mock_uc_factory.return_value = mock_uc

            response = await client.get("/projects")

        body = response.json()
        item = body["items"][0]
        assert "id" in item
        assert item["name"] == "Projeto Alpha"
        assert "is_active" in item
        assert "created_at" in item

    async def test_list_projects_empty_returns_200(self, client):
        """Retorna 200 mesmo quando não há projetos."""
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([])
            mock_uc_factory.return_value = mock_uc

            response = await client.get("/projects")

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_list_projects_invalid_limit_returns_422(self, client):
        """Limit inválido (negativo) retorna 422."""
        response = await client.get("/projects?limit=-1")
        assert response.status_code == 422

    async def test_list_projects_invalid_offset_returns_422(self, client):
        """Offset inválido (negativo) retorna 422."""
        response = await client.get("/projects?offset=-1")
        assert response.status_code == 422


def _make_paginated_response(
    projects: list,
    total: int = 0,
    offset: int = 0,
    limit: int = 20,
):
    from app.application.dtos.list_projects_dto import ListProjectsResponse, ProjectItem

    items = [
        ProjectItem(
            id=p.id,
            name=p.name.value,
            description=p.description.value,
            is_active=p.is_active,
            created_at=p.created_at,
        )
        for p in projects
    ]
    return ListProjectsResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )
