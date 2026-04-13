"""Fixtures para testes E2E.

Os testes E2E verificam fluxos completos do sistema (encurtar → redirecionar → consultar),
usando SQLite em memória para isolamento nos testes de API e Playwright para testes
de interface web real.

Documentação da estratégia em tests/TESTING_STRATEGY.md.
"""

import uuid
from collections.abc import AsyncGenerator, Generator

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.db.models import ApiKeyModel, Base
from app.infrastructure.db.session import get_session
from app.main import create_app
from tests.e2e.seed import TEST_API_KEY

DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"

# URL base do servidor E2E (servidor Docker isolado)
E2E_SERVER_URL = "http://localhost:8001"


# ————————————————————————————————————————————————————
# Fixtures de banco de dados (SQLite in-memory)
# ————————————————————————————————————————————————————


@pytest_asyncio.fixture(scope="function")
async def e2e_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Engine SQLite em memória isolada por função de teste E2E."""
    engine = create_async_engine(
        DATABASE_URL_TEST,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def e2e_session(e2e_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Sessão async conectada ao banco E2E em memória."""
    factory = async_sessionmaker(
        e2e_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def e2e_client(e2e_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP conectado à aplicação com banco E2E isolado.

    Não segue redirects por padrão para permitir verificação de status 302.
    """
    app = create_app()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield e2e_session

    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://e2e-test",
        follow_redirects=False,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def e2e_authenticated_client(
    e2e_session: AsyncSession,
) -> AsyncGenerator[tuple[AsyncClient, str], None]:
    """Cliente HTTP autenticado com API Key real para testes E2E.

    Insere uma ApiKey válida no banco e configura o cliente para usá-la.
    Retorna tupla (cliente, api_key_value).
    """
    app = create_app()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield e2e_session

    app.dependency_overrides[get_session] = override_session

    api_key_value = f"e2e-key-{uuid.uuid4().hex[:16]}"
    api_key_model = ApiKeyModel(
        id=str(uuid.uuid4()),
        key=api_key_value,
        owner="e2e-test-owner",
        is_active=True,
    )
    e2e_session.add(api_key_model)
    await e2e_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://e2e-test",
        follow_redirects=False,
        headers={"X-API-Key": api_key_value},
    ) as ac:
        yield ac, api_key_value

    app.dependency_overrides.clear()


# ————————————————————————————————————————————————————
# Fixtures de URL base e API key para testes contra servidor real
# ————————————————————————————————————————————————————


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    """URL base do servidor E2E em execução no Docker.

    O servidor deve estar rodando antes dos testes.
    Subir com: docker-compose -f docker-compose.e2e.yml up -d
    """
    return E2E_SERVER_URL


@pytest.fixture(scope="session")
def e2e_api_key() -> str:
    """API key de teste para o servidor E2E.

    A API key deve estar previamente inserida no banco via seed.
    """
    return TEST_API_KEY


# ————————————————————————————————————————————————————
# Fixtures Playwright (browser real)
# ————————————————————————————————————————————————————


@pytest.fixture(scope="function")
def browser_context() -> Generator[BrowserContext, None, None]:
    """Contexto de browser Playwright com Chromium headless.

    Criado por teste e destruído após cada execução.
    Requer servidor E2E rodando em http://localhost:8001.
    """
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=True)
        context: BrowserContext = browser.new_context()
        yield context
        context.close()
        browser.close()


@pytest.fixture(scope="function")
def playwright_page(browser_context: BrowserContext) -> Generator[Page, None, None]:
    """Página Playwright para interação com a interface web.

    Criada a partir do browser_context e fechada após cada teste.
    """
    page: Page = browser_context.new_page()
    yield page
    page.close()


# ————————————————————————————————————————————————————
# Fixtures de cliente HTTP (para testes contra servidor real)
# ————————————————————————————————————————————————————


@pytest.fixture(scope="function")
def api_client(e2e_base_url: str, e2e_api_key: str) -> Generator[httpx.Client, None, None]:
    """Cliente HTTP autenticado configurado para o servidor E2E real.

    Usa a API key de seed e aponta para o servidor Docker (porta 8001).
    """
    with httpx.Client(
        base_url=e2e_base_url,
        headers={"X-API-Key": e2e_api_key},
        timeout=30.0,
        follow_redirects=False,
    ) as client:
        yield client


# ————————————————————————————————————————————————————
# Fixture de limpeza de banco (autouse)
# ————————————————————————————————————————————————————


@pytest.fixture(scope="function", autouse=True)
def db_cleanup(request) -> Generator[list[str], None, None]:
    """Fixture de limpeza automática após cada teste E2E contra servidor real.

    Coleta os short_codes criados durante o teste e os remove via API após a execução.
    Apenas ativa para testes que usam a fixture api_client (servidor real).
    Testes que usam SQLite in-memory são limpos automaticamente pela engine.
    """
    created_short_codes: list[str] = []

    # Verificar se o teste usa api_client (servidor real)
    uses_real_server = "api_client" in request.fixturenames

    yield created_short_codes

    # Limpeza apenas para testes contra o servidor real
    if uses_real_server and created_short_codes:
        with httpx.Client(
            base_url=E2E_SERVER_URL,
            headers={"X-API-Key": TEST_API_KEY},
            timeout=10.0,
        ) as cleanup_client:
            for short_code in created_short_codes:
                try:
                    cleanup_client.delete(f"/api/urls/{short_code}")
                except Exception:
                    pass  # Ignora erros de limpeza — melhor esforço
