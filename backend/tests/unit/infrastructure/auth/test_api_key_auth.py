"""Testes unitários para a dependency api_key_auth."""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch

from app.api.dependencies.api_key_auth import api_key_auth
from app.domain.entities.api_key import ApiKey
from tests.helpers import MockApiKeyRepository, MockRedisClient, MockSettings


@pytest.fixture
def mock_api_key_repo_with_valid_key():
    """Repositório com uma chave válida pré-cadastrada."""
    repo = MockApiKeyRepository()
    repo.add_key(ApiKey(key="valid-key-abc12345", owner="test-owner"))
    return repo


@pytest.fixture
def mock_api_key_repo_with_inactive_key():
    """Repositório com uma chave inativa."""
    repo = MockApiKeyRepository()
    repo.add_key(ApiKey(key="inactive-key-xyz", owner="test-owner", is_active=False))
    return repo


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chave_valida_retorna_api_key(mock_api_key_repo_with_valid_key):
    """api_key_auth com chave válida retorna a entidade ApiKey."""
    settings = MockSettings()
    redis = MockRedisClient()

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "app.infrastructure.middleware.rate_limiter.RedisClient",
            lambda s: redis,
        )
        result = await api_key_auth(
            x_api_key="valid-key-abc12345",
            repo=mock_api_key_repo_with_valid_key,
            settings=settings,
        )

    assert result is not None
    assert result.key == "valid-key-abc12345"
    assert result.owner == "test-owner"
    assert result.is_active is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chave_invalida_levanta_401(mock_api_key_repo_with_valid_key):
    """api_key_auth com chave desconhecida levanta HTTPException 401."""
    settings = MockSettings()

    with pytest.raises(HTTPException) as exc_info:
        await api_key_auth(
            x_api_key="chave-invalida-xyz",
            repo=mock_api_key_repo_with_valid_key,
            settings=settings,
        )

    assert exc_info.value.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chave_ausente_levanta_401():
    """api_key_auth sem header X-API-Key (None) levanta HTTPException 401."""
    repo = MockApiKeyRepository()
    settings = MockSettings()

    with pytest.raises(HTTPException) as exc_info:
        await api_key_auth(
            x_api_key=None,
            repo=repo,
            settings=settings,
        )

    assert exc_info.value.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chave_inativa_levanta_401(mock_api_key_repo_with_inactive_key):
    """api_key_auth com chave inativa levanta HTTPException 401."""
    settings = MockSettings()

    with pytest.raises(HTTPException) as exc_info:
        await api_key_auth(
            x_api_key="inactive-key-xyz",
            repo=mock_api_key_repo_with_inactive_key,
            settings=settings,
        )

    assert exc_info.value.status_code == 401
