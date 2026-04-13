"""Mock de Settings para testes unitários."""


class MockSettings:
    """Valores fixos de configuração para testes.

    Substitui o Settings pydantic-settings sem carregar .env ou variáveis de ambiente.
    """

    database_url: str = "sqlite+aiosqlite:///:memory:"
    base_url: str = "http://localhost:8000"
    environment: str = "test"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60
    api_rate_limit_requests: int = 60
