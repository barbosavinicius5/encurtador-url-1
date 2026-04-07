"""Testes de integração para filtros e ordenação no endpoint GET /projects (TASK-005)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.domain.entities.project import Project


def _make_project(name: str = "Projeto Teste") -> Project:
    return Project.create(
        name=name,
        description="Desc",
        account_id=uuid4(),
        created_by=uuid4(),
    )


def _make_paginated_response(projects: list, total: int = 0, offset: int = 0, limit: int = 20):
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
    return ListProjectsResponse(items=items, total=total, offset=offset, limit=limit)


class TestListProjectsFiltersEndpoint:
    """Testes de integração para filtros e ordenação no GET /projects."""

    async def test_filter_by_name_query_param(self, client):
        """Suporta parâmetro name para filtro por nome."""
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([])
            mock_uc_factory.return_value = mock_uc

            response = await client.get("/projects?name=Alpha")

        assert response.status_code == 200

    async def test_order_by_name_query_param(self, client):
        """Suporta parâmetro order_by=name."""
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([])
            mock_uc_factory.return_value = mock_uc

            response = await client.get("/projects?order_by=name")

        assert response.status_code == 200

    async def test_order_by_created_at_query_param(self, client):
        """Suporta parâmetro order_by=created_at."""
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([])
            mock_uc_factory.return_value = mock_uc

            response = await client.get("/projects?order_by=created_at")

        assert response.status_code == 200

    async def test_order_dir_asc_query_param(self, client):
        """Suporta parâmetro order_dir=asc."""
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([])
            mock_uc_factory.return_value = mock_uc

            response = await client.get("/projects?order_dir=asc")

        assert response.status_code == 200

    async def test_order_by_invalid_returns_422(self, client):
        """Parâmetro order_by inválido retorna 422."""
        response = await client.get("/projects?order_by=invalid_field")
        assert response.status_code == 422

    async def test_order_dir_invalid_returns_422(self, client):
        """Parâmetro order_dir inválido retorna 422."""
        response = await client.get("/projects?order_dir=random")
        assert response.status_code == 422

    async def test_all_filters_combined(self, client):
        """Todos os filtros combinados funcionam juntos."""
        with patch("app.infrastructure.di.container.get_list_projects_use_case") as mock_uc_factory:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = _make_paginated_response([])
            mock_uc_factory.return_value = mock_uc

            response = await client.get(
                "/projects?name=Alpha&order_by=name&order_dir=asc&offset=0&limit=10"
            )

        assert response.status_code == 200
