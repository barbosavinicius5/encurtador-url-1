"""Testes unitários para validadores extensíveis de URL."""

import pytest

from app.domain.exceptions import DomainError, MaliciousDomainError
from app.domain.validators.malicious_domain_validator import MaliciousDomainValidator


class TestMaliciousDomainValidator:
    """Testes para o validador de domínios maliciosos."""

    def test_validate_url_limpa_nao_lanca_excecao(self):
        validator = MaliciousDomainValidator(blocked_domains=["phishing.com"])
        # Não deve lançar exceção
        validator.validate("https://safe-site.com/path")

    def test_validate_url_com_dominio_bloqueado_lanca_error(self):
        validator = MaliciousDomainValidator(blocked_domains=["phishing.com"])
        with pytest.raises(MaliciousDomainError) as exc:
            validator.validate("https://phishing.com/login")
        assert exc.value.domain == "phishing.com"

    def test_validate_subdomain_bloqueado(self):
        validator = MaliciousDomainValidator(blocked_domains=["phishing.com"])
        with pytest.raises(MaliciousDomainError):
            validator.validate("https://sub.phishing.com/page")

    def test_validate_e_case_insensitive(self):
        validator = MaliciousDomainValidator(blocked_domains=["PHISHING.COM"])
        with pytest.raises(MaliciousDomainError):
            validator.validate("https://phishing.com/login")

    def test_validate_blocklist_vazia_aceita_qualquer_url(self):
        validator = MaliciousDomainValidator(blocked_domains=[])
        # Não deve lançar exceção
        validator.validate("https://qualquer.com")

    def test_validate_implementa_protocolo_validador(self):
        """MaliciousDomainValidator deve ter método validate(url: str) -> None."""
        validator = MaliciousDomainValidator(blocked_domains=[])
        assert hasattr(validator, "validate")
        assert callable(validator.validate)

    def test_validate_lanca_domain_error(self):
        """MaliciousDomainError deve herdar de DomainError."""
        validator = MaliciousDomainValidator(blocked_domains=["phishing.com"])
        with pytest.raises(DomainError):
            validator.validate("https://phishing.com/login")
