"""Configurações e fixtures compartilhadas para os testes."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import create_app


@pytest.fixture
def app():
    """Fixture que cria a aplicação FastAPI para testes."""
    return create_app()


@pytest.fixture
async def client(app):
    """Fixture que fornece um cliente HTTP async para testes de integração."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
