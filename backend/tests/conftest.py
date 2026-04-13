"""Configurações e fixtures compartilhadas para os testes."""

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from tests.helpers import MockApiKeyRepository, MockRedisClient, MockSettings, MockUrlRepository

# ————————————————————————————————————————————————————
# Fixtures de respostas determinísticas de IA
# ————————————————————————————————————————————————————

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ai_responses"


@pytest.fixture(scope="session")
def ai_response_fixture():
    """Fixture que carrega payloads JSON determinísticos de respostas de agentes de IA.

    Retorna uma função que aceita o nome do arquivo (sem extensão) e retorna dict Python.
    Os arquivos ficam em tests/fixtures/ai_responses/*.json e são versionados junto ao código.

    Uso:
        def test_algo(ai_response_fixture):
            payload = ai_response_fixture("generate_short_code")
            assert payload["choices"][0]["message"]["content"] == "aB12x"

    Raises:
        FileNotFoundError: Se o arquivo de fixture não existir, com path completo na mensagem.
    """

    def _load(name: str) -> dict:
        path = FIXTURES_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"Fixture de IA não encontrada: {path}. "
                f"Arquivos disponíveis: {list(FIXTURES_DIR.glob('*.json'))}"
            )
        return json.loads(path.read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def app():
    """Fixture que cria a aplicação FastAPI para testes."""
    return create_app()


@pytest.fixture
async def client(app):
    """Fixture que fornece um cliente HTTP async para testes de integração."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ————————————————————————————————————————————————————
# Fixtures unitárias (sem I/O real)
# ————————————————————————————————————————————————————


@pytest.fixture(scope="function")
def mock_url_repo() -> MockUrlRepository:
    """Fixture que fornece um MockUrlRepository limpo por teste."""
    return MockUrlRepository()


@pytest.fixture(scope="function")
def mock_api_key_repo() -> MockApiKeyRepository:
    """Fixture que fornece um MockApiKeyRepository limpo por teste."""
    return MockApiKeyRepository()


@pytest.fixture(scope="function")
def mock_redis() -> MockRedisClient:
    """Fixture que fornece um MockRedisClient limpo por teste."""
    return MockRedisClient()


@pytest.fixture(scope="function")
def mock_settings() -> MockSettings:
    """Fixture que fornece um MockSettings com valores fixos por teste."""
    return MockSettings()
