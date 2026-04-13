"""Fixtures de infraestrutura para testes de integração.

Fornece banco SQLite em memória isolado por função, override de dependências FastAPI,
interceptadores HTTP para serviços externos e cliente HTTP para testes end-to-end.

Estratégia de banco: sqlite+aiosqlite:///:memory: — um novo banco por função de teste,
criado e destruído automaticamente. Detalhes em tests/TESTING_STRATEGY.md.
"""

import logging
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.db.models import Base
from app.infrastructure.db.session import get_session
from app.main import create_app

logger = logging.getLogger(__name__)

DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"


# ─────────────────────────────────────────────────────────────
# Fixtures de banco de dados isolado por função
# ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="function")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Cria um AsyncEngine SQLite em memória isolado por teste.

    Cada função de teste recebe um banco completamente novo com schema criado.
    O banco é descartado automaticamente ao final do teste.
    """
    engine = create_async_engine(
        DATABASE_URL_TEST,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    logger.debug("Banco de teste criado: %s", DATABASE_URL_TEST)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    logger.debug("Banco de teste descartado")


@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Fornece uma AsyncSession conectada ao banco de teste em memória.

    A sessão é configurada com expire_on_commit=False para permitir acesso
    a atributos após o commit sem recarregar do banco.
    """
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with async_session_factory() as session:
        yield session


# ─────────────────────────────────────────────────────────────
# Fixtures de cliente HTTP com banco de teste injetado
# ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="function")
async def app_with_db(test_db_session: AsyncSession):
    """Cria a aplicação FastAPI com banco de teste injetado via dependency_overrides.

    Override de get_session para usar o banco SQLite em memória.
    Override de api_key_auth desabilitado — cada teste de auth injeta seu próprio mock.
    """
    application = create_app()

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    application.dependency_overrides[get_session] = override_get_session

    yield application

    application.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client(app_with_db) -> AsyncGenerator[AsyncClient, None]:
    """Fornece um AsyncClient HTTP conectado à aplicação com banco de teste.

    Não segue redirects por padrão para permitir verificação de status 302.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app_with_db),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(app_with_db, test_db_session: AsyncSession):
    """Fornece um AsyncClient com autenticação via API Key real no banco de teste.

    Insere uma ApiKey válida no banco e configura o cliente para usá-la.
    """
    from app.infrastructure.db.models import ApiKeyModel

    # Insere ApiKey válida diretamente no banco de teste
    api_key_value = f"test-api-key-{uuid.uuid4().hex[:16]}"
    api_key_model = ApiKeyModel(
        id=str(uuid.uuid4()),
        key=api_key_value,
        owner="test-owner",
        is_active=True,
    )
    test_db_session.add(api_key_model)
    await test_db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app_with_db),
        base_url="http://test",
        follow_redirects=False,
        headers={"X-API-Key": api_key_value},
    ) as ac:
        yield ac, api_key_value


# ─────────────────────────────────────────────────────────────
# Fixtures de interceptação HTTP para serviços externos
# ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def block_external_http():
    """Intercepta chamadas HTTP a serviços externos, bloqueando-as por padrão.

    Qualquer requisição HTTP real a domínios externos durante os testes
    levanta ConnectionError com mensagem descritiva.

    Como registrar um mock permitido em um teste específico:
        def test_algo(block_external_http):
            # O fixture retorna um dicionário de handlers registrados
            # que podem ser consultados para verificar chamadas
            pass

    Nota: Este fixture usa monkeypatching de httpx para bloquear chamadas externas.
    Para permitir chamadas específicas, use respx (se instalado) ou mock direto.
    """
    blocked_domains = [
        "api.github.com",
        "api.atlassian.com",
        "api.openai.com",
        "api.anthropic.com",
    ]

    try:
        import respx

        # assert_all_mocked=False: permite rotas não registradas (não bloqueia tudo)
        # assert_all_called=False: não exige que todas as rotas registradas sejam chamadas
        with respx.mock(assert_all_mocked=False, assert_all_called=False) as mock_router:
            for domain in blocked_domains:
                mock_router.route(host=domain).mock(
                    side_effect=ConnectionError(
                        f"Chamada HTTP bloqueada em testes: {domain}. "
                        "Use fixtures de mock para simular respostas."
                    )
                )
            yield mock_router

    except ImportError:
        # Fallback: sem respx, apenas yield sem bloqueio ativo
        # (testes de bloqueio serão marcados como skip)
        logger.warning("respx não instalado — interceptação HTTP não ativa")
        yield None


# ─────────────────────────────────────────────────────────────
# Fixtures auxiliares para rate limiter
# ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def mock_rate_limiter(app_with_db):
    """Desativa rate limiting para testes que não precisam testá-lo.

    Retorna a aplicação com rate limiter mockado (sempre permitido).
    """
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
        new_callable=lambda: lambda: AsyncMock(return_value=None),
    ):
        yield app_with_db


@pytest_asyncio.fixture(scope="function")
async def client_no_rate_limit(app_with_db, test_db_session: AsyncSession):
    """Cliente HTTP sem rate limiting ativo, com banco de teste injetado.

    Insere uma ApiKey válida e bypassa o rate limiter para testes de negócio.
    """
    from unittest.mock import patch

    from app.infrastructure.db.models import ApiKeyModel

    api_key_value = f"test-api-key-{uuid.uuid4().hex[:16]}"
    api_key_model = ApiKeyModel(
        id=str(uuid.uuid4()),
        key=api_key_value,
        owner="test-owner-no-rl",
        is_active=True,
    )
    test_db_session.add(api_key_model)
    await test_db_session.commit()

    with patch(
        "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
        new=AsyncMock(return_value=None),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
            headers={"X-API-Key": api_key_value},
        ) as ac:
            yield ac, api_key_value, test_db_session


# ─────────────────────────────────────────────────────────────
# Aliases para compatibilidade com testes de smoke (T001)
# ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="function")
async def db_session(test_db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Alias para test_db_session — compatibilidade com testes de smoke.

    Fornece sessão async conectada ao banco SQLite em memória por função.
    """
    yield test_db_session


@pytest_asyncio.fixture(scope="function")
async def integration_client(client_no_rate_limit):
    """Alias para client_no_rate_limit — cliente com banco real e sem rate limit.

    Retorna apenas o cliente (sem tuple) para simplificar testes de smoke.
    """
    client, api_key_value, _ = client_no_rate_limit
    yield client
