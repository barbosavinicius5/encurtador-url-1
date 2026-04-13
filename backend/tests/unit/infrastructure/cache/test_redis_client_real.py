"""Testes unitários para RedisClient (classe de produção) usando mocks."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.cache.redis_client import RedisClient
from tests.helpers import MockSettings


@pytest.fixture
def settings():
    return MockSettings()


@pytest.fixture
def mock_aioredis_client():
    """Mock do cliente redis.asyncio subjacente."""
    client = AsyncMock()
    return client


@pytest.fixture
def redis_client_with_mock(settings, mock_aioredis_client):
    """RedisClient com o cliente interno substituído por mock."""
    with patch(
        "app.infrastructure.cache.redis_client.aioredis.from_url", return_value=mock_aioredis_client
    ):
        client = RedisClient(settings)
    return client, mock_aioredis_client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_client_get_retorna_valor(redis_client_with_mock):
    """RedisClient.get retorna o valor do Redis."""
    client, mock_inner = redis_client_with_mock
    mock_inner.get.return_value = "valor-teste"

    result = await client.get("chave")
    assert result == "valor-teste"
    mock_inner.get.assert_called_once_with("chave")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_client_get_retorna_none_quando_erro(redis_client_with_mock):
    """RedisClient.get retorna None quando Redis levanta exceção (fail-safe)."""
    client, mock_inner = redis_client_with_mock
    mock_inner.get.side_effect = ConnectionError("Redis indisponível")

    result = await client.get("chave")
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_client_set_chama_setex(redis_client_with_mock):
    """RedisClient.set chama setex com os parâmetros corretos."""
    client, mock_inner = redis_client_with_mock
    mock_inner.setex.return_value = None

    await client.set("chave", "valor", ttl_seconds=300)
    mock_inner.setex.assert_called_once_with("chave", 300, "valor")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_client_set_silencia_erro(redis_client_with_mock):
    """RedisClient.set não propaga exceção quando Redis falha."""
    client, mock_inner = redis_client_with_mock
    mock_inner.setex.side_effect = ConnectionError("Redis indisponível")

    # Não deve lançar exceção
    await client.set("chave", "valor")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_client_increment_with_ttl_retorna_novo_valor(redis_client_with_mock):
    """RedisClient.increment_with_ttl retorna o valor incrementado."""
    client, mock_inner = redis_client_with_mock
    # pipeline() é síncrono (retorna pipeline object), não coroutine
    mock_pipeline = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[5, True])
    # pipeline é síncrono — forçamos retorno síncrono
    mock_inner.pipeline = MagicMock(return_value=mock_pipeline)

    result = await client.increment_with_ttl("contador")
    assert result == 5
    mock_pipeline.incr.assert_called_once_with("contador")
    mock_pipeline.expire.assert_called_once_with("contador", 60, xx=False)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_client_close_chama_aclose(redis_client_with_mock):
    """RedisClient.close chama aclose no cliente interno."""
    client, mock_inner = redis_client_with_mock
    mock_inner.aclose.return_value = None

    await client.close()
    mock_inner.aclose.assert_called_once()
