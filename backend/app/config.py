"""Configurações da aplicação via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener"
    base_url: str = "https://short.app"
    environment: str = "development"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60
    api_rate_limit_requests: int = 60


@lru_cache
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()
