"""Testes unitários para o rate_limiter middleware."""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock

from app.infrastructure.middleware.rate_limiter import rate_limit_by_ip, rate_limit_by_api_key
from tests.helpers import MockRedisClient, MockSettings


def make_mock_request(ip: str = "127.0.0.1"):
    """Cria um mock de Request FastAPI com o IP configurado."""
    mock_request = MagicMock()
    mock_request.client.host = ip
    return mock_request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_by_ip_permite_primeira_requisicao():
    """rate_limit_by_ip permite a primeira requisição (contador = 1)."""
    redis = MockRedisClient()
    settings = MockSettings()
    request = make_mock_request("192.168.1.1")

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "app.infrastructure.middleware.rate_limiter.RedisClient",
            lambda s: redis,
        )
        # Não deve lançar exceção
        await rate_limit_by_ip(request=request, settings=settings)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_by_ip_bloqueia_apos_limite():
    """rate_limit_by_ip levanta HTTPException 429 quando limite é excedido."""
    redis = MockRedisClient()
    settings = MockSettings()
    settings.rate_limit_requests = 2
    request = make_mock_request("10.0.0.1")

    # Pré-encher o contador além do limite
    for _ in range(settings.rate_limit_requests):
        await redis.increment_with_ttl(f"rate_limit:10.0.0.1")

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "app.infrastructure.middleware.rate_limiter.RedisClient",
            lambda s: redis,
        )
        with pytest.raises(HTTPException) as exc_info:
            await rate_limit_by_ip(request=request, settings=settings)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_by_ip_fail_open_quando_redis_indisponivel():
    """rate_limit_by_ip não bloqueia quando Redis lança exceção (fail-open)."""
    settings = MockSettings()
    request = make_mock_request("172.0.0.1")

    class BrokenRedis:
        async def increment_with_ttl(self, *args, **kwargs):
            raise ConnectionError("Redis indisponível")

        async def close(self):
            pass

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "app.infrastructure.middleware.rate_limiter.RedisClient",
            lambda s: BrokenRedis(),
        )
        # Não deve lançar HTTPException — fail-open
        await rate_limit_by_ip(request=request, settings=settings)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_by_api_key_permite_primeira_requisicao():
    """rate_limit_by_api_key permite a primeira requisição."""
    redis = MockRedisClient()
    settings = MockSettings()

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "app.infrastructure.middleware.rate_limiter.RedisClient",
            lambda s: redis,
        )
        # Não deve lançar exceção
        await rate_limit_by_api_key(api_key_value="test-key-abc123", settings=settings)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_by_api_key_bloqueia_apos_limite():
    """rate_limit_by_api_key levanta HTTPException 429 quando limite é excedido."""
    redis = MockRedisClient()
    settings = MockSettings()
    settings.api_rate_limit_requests = 2
    api_key_value = "test-key-blocked"

    # Pré-encher o contador além do limite
    for _ in range(settings.api_rate_limit_requests):
        await redis.increment_with_ttl(f"rate_limit:apikey:{api_key_value}")

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "app.infrastructure.middleware.rate_limiter.RedisClient",
            lambda s: redis,
        )
        with pytest.raises(HTTPException) as exc_info:
            await rate_limit_by_api_key(api_key_value=api_key_value, settings=settings)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers
