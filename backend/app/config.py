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
    # blocked_domains é armazenado como string CSV para compatibilidade com pydantic-settings v2
    # Use a propriedade blocked_domains_list para obter a lista parseada
    blocked_domains_csv: str = ""
    cache_ttl_seconds: int = 3600  # TTL do cache de redirecionamento (segundos)

    # Brute force detection — parâmetros de detecção de força bruta/varredura abusiva
    brute_force_threshold_multiplier: int = 3  # Fator: RATE_LIMIT_REQUESTS × multiplier = threshold
    brute_force_detection_window_seconds: int = 300  # Janela expandida de detecção (5 min)
    brute_force_block_seconds: int = 3600  # Duração do bloqueio progressivo (1 hora)

    @property
    def blocked_domains(self) -> list[str]:
        """Retorna a lista de domínios bloqueados parseada do CSV."""
        return [d.strip() for d in self.blocked_domains_csv.split(",") if d.strip()]


@lru_cache
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()
