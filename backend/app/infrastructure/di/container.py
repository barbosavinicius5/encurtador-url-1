"""Container de injeção de dependências da aplicação."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.redirect_url_use_case import RedirectUrlUseCase
from app.application.use_cases.shorten_url_use_case import ShortenUrlUseCase
from app.config import Settings, get_settings
from app.infrastructure.cache.redis_client import RedisClient
from app.infrastructure.db.repositories.url_repository import PostgreSQLUrlRepository
from app.infrastructure.db.session import get_session


async def get_redis_client(
    settings: Settings = Depends(get_settings),
) -> RedisClient:
    """Dependency que fornece um cliente Redis configurado."""
    return RedisClient(settings)


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
