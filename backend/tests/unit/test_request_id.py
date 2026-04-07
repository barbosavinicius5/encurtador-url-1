"""Testes unitários para o módulo de request_id (contextvars)."""

from app.core.request_id import get_request_id, set_request_id


class TestRequestIdContextVar:
    """Testa o módulo de request_id com contextvars."""

    def test_get_request_id_retorna_na_sem_contexto(self):
        """Sem contexto HTTP ativo e após reset, deve retornar 'N/A'."""
        # Reset explícito para garantir valor padrão neste teste
        set_request_id("N/A")
        result = get_request_id()
        assert result == "N/A"

    def test_set_e_get_request_id(self):
        """Deve armazenar e recuperar o request_id corretamente."""
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        set_request_id(test_id)
        result = get_request_id()
        assert result == test_id

    def test_request_id_eh_string(self):
        """O valor retornado deve sempre ser uma string."""
        result = get_request_id()
        assert isinstance(result, str)

    def test_set_request_id_substitui_valor_anterior(self):
        """Chamar set_request_id múltiplas vezes substitui o valor."""
        set_request_id("id-antigo-123")
        set_request_id("id-novo-456")
        assert get_request_id() == "id-novo-456"
