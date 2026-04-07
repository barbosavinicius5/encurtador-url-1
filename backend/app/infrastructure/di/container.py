"""Container de injeção de dependências da aplicação."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.create_project_use_case import CreateProjectUseCase
from app.application.use_cases.get_url_details_use_case import GetUrlDetailsUseCase
from app.application.use_cases.list_links_use_case import ListLinksUseCase
from app.application.use_cases.list_projects_use_case import ListProjectsUseCase
from app.application.use_cases.redirect_url_use_case import RedirectUrlUseCase
from app.application.use_cases.shorten_url_use_case import ShortenUrlUseCase
from app.config import Settings, get_settings
from app.infrastructure.cache.redis_client import RedisClient
from app.infrastructure.db.repositories.api_key_repository import PostgreSQLApiKeyRepository
from app.infrastructure.db.repositories.project_repository import PostgreSQLProjectRepository
from app.infrastructure.db.repositories.url_repository import PostgreSQLUrlRepository
from app.infrastructure.db.session import get_session


async def get_redis_client(
    settings: Settings = Depends(get_settings),
) -> RedisClient:
    """Dependency que fornece um cliente Redis configurado."""
    return RedisClient(settings)


async def get_api_key_repository(
    session: AsyncSession = Depends(get_session),
) -> PostgreSQLApiKeyRepository:
    """Dependency que fornece o repositório de API Keys configurado."""
    return PostgreSQLApiKeyRepository(session)


async def get_shorten_use_case(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ShortenUrlUseCase:
    """Dependency que fornece o use case de encurtamento configurado."""
    repository = PostgreSQLUrlRepository(session)
    return ShortenUrlUseCase(repository=repository, settings=settings)


async def get_redirect_use_case(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cache: RedisClient = Depends(get_redis_client),
) -> RedirectUrlUseCase:
    """Dependency que fornece o use case de redirect configurado."""
    repository = PostgreSQLUrlRepository(session)
    return RedirectUrlUseCase(repository=repository, cache=cache)


async def get_list_links_use_case(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ListLinksUseCase:
    """Dependency que fornece o use case de listagem de links configurado."""
    repository = PostgreSQLUrlRepository(session)
    return ListLinksUseCase(repository=repository)


async def get_url_details_use_case(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> GetUrlDetailsUseCase:
    """Dependency que fornece o use case de detalhes de URL configurado."""
    repository = PostgreSQLUrlRepository(session)
    return GetUrlDetailsUseCase(repository=repository, base_url=settings.base_url)


async def get_create_project_use_case(
    session: AsyncSession = Depends(get_session),
) -> CreateProjectUseCase:
    """Dependency que fornece o use case de criação de projeto configurado."""
    repository = PostgreSQLProjectRepository(session)
    return CreateProjectUseCase(repository=repository)


async def get_list_projects_use_case(
    session: AsyncSession = Depends(get_session),
) -> ListProjectsUseCase:
    """Dependency que fornece o use case de listagem de projetos configurado."""
    repository = PostgreSQLProjectRepository(session)
    return ListProjectsUseCase(repository=repository)
