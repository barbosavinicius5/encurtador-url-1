"""Testes unitários para as exceptions de domínio."""


from app.domain.exceptions import (
    DomainError,
    InvalidUrlError,
    MaliciousDomainError,
    SlugCollisionError,
)


class TestDomainError:
    """Testes para a classe base DomainError."""

    def test_domain_error_e_exception(self):
        error = DomainError("mensagem")
        assert isinstance(error, Exception)

    def test_domain_error_mensagem(self):
        error = DomainError("mensagem de teste")
        assert str(error) == "mensagem de teste"


class TestInvalidUrlError:
    """Testes para InvalidUrlError."""

    def test_instanciar_invalid_url_error(self):
        error = InvalidUrlError(url="ftp://exemplo.com", reason="scheme 'ftp' não permitido")
        assert error.url == "ftp://exemplo.com"
        assert error.reason == "scheme 'ftp' não permitido"

    def test_invalid_url_error_herda_domain_error(self):
        error = InvalidUrlError(url="ftp://exemplo.com", reason="scheme inválido")
        assert isinstance(error, DomainError)

    def test_invalid_url_error_herda_value_error(self):
        """InvalidUrlError deve herdar de ValueError para compatibilidade retroativa."""
        error = InvalidUrlError(url="ftp://exemplo.com", reason="scheme inválido")
        assert isinstance(error, ValueError)

    def test_invalid_url_error_str_contem_url(self):
        error = InvalidUrlError(url="ftp://exemplo.com", reason="scheme 'ftp' não permitido")
        assert "ftp://exemplo.com" in str(error)

    def test_invalid_url_error_str_contem_reason(self):
        error = InvalidUrlError(url="ftp://exemplo.com", reason="scheme 'ftp' não permitido")
        assert "scheme 'ftp' não permitido" in str(error)

    def test_invalid_url_error_atributos(self):
        error = InvalidUrlError(url="https://", reason="host ausente")
        assert error.url == "https://"
        assert error.reason == "host ausente"


class TestMaliciousDomainError:
    """Testes para MaliciousDomainError."""

    def test_instanciar_malicious_domain_error(self):
        error = MaliciousDomainError(domain="phishing.com")
        assert error.domain == "phishing.com"

    def test_malicious_domain_error_herda_domain_error(self):
        error = MaliciousDomainError(domain="phishing.com")
        assert isinstance(error, DomainError)

    def test_malicious_domain_error_str_contem_dominio(self):
        error = MaliciousDomainError(domain="phishing.com")
        assert "phishing.com" in str(error)

    def test_malicious_domain_error_domain_atributo(self):
        error = MaliciousDomainError(domain="malware.net")
        assert error.domain == "malware.net"


class TestSlugCollisionError:
    """Testes para SlugCollisionError."""

    def test_instanciar_slug_collision_error(self):
        error = SlugCollisionError(slug="abc123")
        assert error.slug == "abc123"

    def test_slug_collision_error_herda_domain_error(self):
        error = SlugCollisionError(slug="abc123")
        assert isinstance(error, DomainError)

    def test_slug_collision_error_str_contem_slug(self):
        error = SlugCollisionError(slug="abc123")
        assert "abc123" in str(error)

    def test_slug_collision_error_slug_atributo(self):
        error = SlugCollisionError(slug="xyz789")
        assert error.slug == "xyz789"
