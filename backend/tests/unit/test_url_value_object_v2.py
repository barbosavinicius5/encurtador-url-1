"""Testes unitários para o value object UrlValue com validação RFC 3986 e blocklist."""

import pytest

from app.domain.exceptions import InvalidUrlError, MaliciousDomainError
from app.domain.value_objects.url import UrlValue


class TestUrlValueRFC3986:
    """Testes para validação RFC 3986 no UrlValue."""

    def test_url_valida_https_aceita(self):
        url = UrlValue(url="https://www.exemplo.com/produtos?cat=1")
        assert url.value == "https://www.exemplo.com/produtos?cat=1"

    def test_url_valida_http_aceita(self):
        url = UrlValue(url="http://exemplo.com")
        assert url.value == "http://exemplo.com"

    def test_url_com_scheme_ftp_rejeitada(self):
        with pytest.raises(InvalidUrlError) as exc:
            UrlValue(url="ftp://arquivo.exemplo.com")
        assert "scheme" in exc.value.reason.lower()

    def test_url_sem_scheme_rejeitada(self):
        with pytest.raises(InvalidUrlError):
            UrlValue(url="www.exemplo.com/path")

    def test_url_com_host_vazio_rejeitada(self):
        with pytest.raises(InvalidUrlError) as exc:
            UrlValue(url="https://")
        assert "host" in exc.value.reason.lower()

    def test_url_invalida_lanca_invalid_url_error(self):
        with pytest.raises(InvalidUrlError):
            UrlValue(url="nao-e-uma-url")

    def test_invalid_url_error_eh_value_error(self):
        """InvalidUrlError deve ser capturável como ValueError para retrocompatibilidade."""
        with pytest.raises(ValueError):
            UrlValue(url="ftp://arquivo.exemplo.com")

    def test_url_com_path_e_query_aceita(self):
        url = UrlValue(url="https://exemplo.com/path?q=1&foo=bar")
        assert "https://exemplo.com/path" in url.value

    def test_url_com_port_aceita(self):
        url = UrlValue(url="http://localhost:8080/api")
        assert url.value == "http://localhost:8080/api"

    def test_url_value_e_imutavel(self):
        url = UrlValue(url="https://exemplo.com")
        with pytest.raises(AttributeError):
            url.value = "https://outro.com"


class TestUrlValueBlocklist:
    """Testes para blocklist de domínios maliciosos no UrlValue."""

    def test_url_com_dominio_na_blocklist_rejeitada(self):
        with pytest.raises(MaliciousDomainError) as exc:
            UrlValue(
                url="https://phishing.com/login",
                blocked_domains=["phishing.com", "malware.net"],
            )
        assert exc.value.domain == "phishing.com"

    def test_subdomain_de_dominio_bloqueado_rejeitado(self):
        with pytest.raises(MaliciousDomainError):
            UrlValue(
                url="https://sub.phishing.com/page",
                blocked_domains=["phishing.com"],
            )

    def test_url_com_dominio_fora_da_blocklist_aceita(self):
        url = UrlValue(
            url="https://safe-site.com/page",
            blocked_domains=["phishing.com"],
        )
        assert url.value == "https://safe-site.com/page"

    def test_comparacao_blocklist_case_insensitive(self):
        with pytest.raises(MaliciousDomainError):
            UrlValue(
                url="https://phishing.com/login",
                blocked_domains=["PHISHING.COM"],
            )

    def test_url_com_subdomain_nao_bloqueado_aceita(self):
        url = UrlValue(
            url="https://safe.outro.com/page",
            blocked_domains=["phishing.com"],
        )
        assert url.value is not None

    def test_blocklist_vazia_aceita_qualquer_url_valida(self):
        url = UrlValue(
            url="https://exemplo.com",
            blocked_domains=[],
        )
        assert url.value == "https://exemplo.com"

    def test_blocklist_padrao_vazia(self):
        """Sem passar blocked_domains, nenhum domínio é bloqueado."""
        url = UrlValue(url="https://qualquer.com")
        assert url.value == "https://qualquer.com"

    def test_malicious_domain_error_carrega_dominio(self):
        with pytest.raises(MaliciousDomainError) as exc:
            UrlValue(
                url="https://malware.net/page",
                blocked_domains=["malware.net"],
            )
        assert exc.value.domain == "malware.net"


class TestUrlValueSanitizacao:
    """Testes de sanitização integrada no UrlValue."""

    def test_url_com_espacos_e_sanitizada_e_aceita(self):
        url = UrlValue(url="  https://exemplo.com  ")
        assert url.value == "https://exemplo.com"

    def test_url_com_scheme_uppercase_e_normalizada(self):
        url = UrlValue(url="HTTPS://exemplo.com")
        assert url.value == "https://exemplo.com"
