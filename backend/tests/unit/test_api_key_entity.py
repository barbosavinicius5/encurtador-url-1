"""Testes unitários para a entidade ApiKey."""

from datetime import UTC, datetime

import pytest

from app.domain.entities.api_key import ApiKey


@pytest.mark.unit
class TestApiKeyEntity:
    """Testes para a entidade de domínio ApiKey."""

    def test_criar_api_key_com_campos_obrigatorios(self):
        """ApiKey deve ser criada com key e owner."""
        api_key = ApiKey(key="test-key-123", owner="empresa-x")

        assert api_key.key == "test-key-123"
        assert api_key.owner == "empresa-x"

    def test_api_key_ativa_por_padrao(self):
        """ApiKey deve estar ativa por padrão."""
        api_key = ApiKey(key="test-key", owner="owner")

        assert api_key.is_active is True

    def test_api_key_com_is_active_false(self):
        """ApiKey pode ser criada como inativa."""
        api_key = ApiKey(key="test-key", owner="owner", is_active=False)

        assert api_key.is_active is False

    def test_api_key_created_at_preenchido_automaticamente(self):
        """created_at deve ser preenchido automaticamente na criação."""
        before = datetime.now(UTC)
        api_key = ApiKey(key="test-key", owner="owner")
        after = datetime.now(UTC)

        assert before <= api_key.created_at <= after

    def test_api_key_id_pode_ser_none(self):
        """id pode ser None (antes de persistir)."""
        api_key = ApiKey(key="test-key", owner="owner")

        assert api_key.id is None

    def test_api_key_com_id_explicito(self):
        """id pode ser definido explicitamente."""
        api_key = ApiKey(key="test-key", owner="owner", id="uuid-123")

        assert api_key.id == "uuid-123"
