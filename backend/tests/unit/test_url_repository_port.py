"""Testes para validar que o port UrlRepositoryPort possui o método find_by_original_url_and_session."""

import inspect

from app.domain.ports.url_repository_port import UrlRepositoryPort


class TestUrlRepositoryPortContract:
    """Testes para o contrato do port de repositório de URLs."""

    def test_port_possui_metodo_find_by_original_url_and_session(self):
        """O port deve declarar o método find_by_original_url_and_session."""
        assert hasattr(UrlRepositoryPort, "find_by_original_url_and_session"), (
            "UrlRepositoryPort deve ter o método find_by_original_url_and_session"
        )

    def test_metodo_find_by_original_url_and_session_e_abstrato(self):
        """O método find_by_original_url_and_session deve ser abstrato."""
        method = getattr(UrlRepositoryPort, "find_by_original_url_and_session", None)
        assert method is not None
        assert getattr(method, "__isabstractmethod__", False), (
            "find_by_original_url_and_session deve ser um método abstrato"
        )

    def test_metodo_aceita_parametros_corretos(self):
        """O método deve aceitar original_url e session_id como parâmetros."""
        method = getattr(UrlRepositoryPort, "find_by_original_url_and_session")
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert "original_url" in params, "Deve ter parâmetro original_url"
        assert "session_id" in params, "Deve ter parâmetro session_id"
