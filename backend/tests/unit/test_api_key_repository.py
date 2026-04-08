"""Testes unitários para PostgreSQLApiKeyRepository."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.entities.api_key import ApiKey
from app.infrastructure.db.repositories.api_key_repository import PostgreSQLApiKeyRepository


def _make_api_key_model(
    id="key-id-1",
    key="test-api-key-12345678",
    owner="test-owner",
    is_active=True,
):
    model = MagicMock()
    model.id = id
    model.key = key
    model.owner = owner
    model.is_active = is_active
    model.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return model


class TestPostgreSQLApiKeyRepository:
    """Testes para PostgreSQLApiKeyRepository."""

    @pytest.mark.asyncio
    async def test_get_by_key_retorna_entidade_quando_existe(self):
        """get_by_key() deve retornar ApiKey quando chave existe."""
        session = AsyncMock()
        model = _make_api_key_model()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = model
        session.execute = AsyncMock(return_value=result_mock)

        repo = PostgreSQLApiKeyRepository(session)
        api_key = await repo.get_by_key("test-api-key-12345678")

        assert api_key is not None
        assert api_key.key == "test-api-key-12345678"
        assert api_key.owner == "test-owner"
        assert api_key.is_active is True

    @pytest.mark.asyncio
    async def test_get_by_key_retorna_none_quando_nao_existe(self):
        """get_by_key() deve retornar None quando chave não existe."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = PostgreSQLApiKeyRepository(session)
        api_key = await repo.get_by_key("chave-inexistente")

        assert api_key is None

    @pytest.mark.asyncio
    async def test_save_persiste_api_key_e_retorna_entidade(self):
        """save() deve persistir e retornar ApiKey com dados corretos."""
        session = AsyncMock()
        model = _make_api_key_model(id="new-id", key="nova-chave-12345678")
        session.flush = AsyncMock()
        session.refresh = AsyncMock(side_effect=lambda m: None)

        with patch(
            "app.infrastructure.db.repositories.api_key_repository.ApiKeyModel",
            return_value=model,
        ):
            repo = PostgreSQLApiKeyRepository(session)
            api_key = ApiKey(
                id=None,
                key="nova-chave-12345678",
                owner="novo-owner",
                is_active=True,
            )
            result = await repo.save(api_key)

        assert result.key == "nova-chave-12345678"
        assert result.owner == "test-owner"  # do model mock
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_key_retorna_api_key_inativa(self):
        """get_by_key() deve retornar ApiKey inativa quando is_active=False."""
        session = AsyncMock()
        model = _make_api_key_model(is_active=False)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = model
        session.execute = AsyncMock(return_value=result_mock)

        repo = PostgreSQLApiKeyRepository(session)
        api_key = await repo.get_by_key("test-api-key-12345678")

        assert api_key is not None
        assert api_key.is_active is False
