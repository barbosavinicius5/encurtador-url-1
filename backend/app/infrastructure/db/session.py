"""Configuração de sessão async do SQLAlchemy."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_engine = None
_AsyncSessionLocal = None


def _get_engine():
    """Retorna o engine, criando-o na primeira chamada (lazy initialization)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.environment == "development",
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=30,
        )
    return _engine


def _get_session_factory():
    """Retorna a session factory, criando-a na primeira chamada (lazy initialization)."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _AsyncSessionLocal


def get_session_factory() -> async_sessionmaker:
    """Retorna a session factory para uso em background tasks."""
    return _get_session_factory()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency que fornece uma sessão async do banco de dados."""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
