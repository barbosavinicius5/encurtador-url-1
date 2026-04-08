"""Testes unitários para o value object UrlValue."""

import pytest

from app.domain.value_objects.url import UrlValue


class TestUrlValueObject:
    """Testes para validação de URL."""

    def test_url_valida_http(self):
        url = UrlValue(url="http://exemplo.com")
        assert url.value == "http://exemplo.com"

    def test_url_valida_https(self):
        url = UrlValue(url="https://exemplo.com/pagina-longa")
        assert url.value == "https://exemplo.com/pagina-longa"

    def test_url_valida_com_path(self):
        url = UrlValue(url="https://www.exemplo.com/artigo/como-usar?q=teste")
        assert url.value == "https://www.exemplo.com/artigo/como-usar?q=teste"

    def test_url_valida_localhost(self):
        url = UrlValue(url="http://localhost:8000/api")
        assert url.value == "http://localhost:8000/api"

    def test_url_sem_protocolo_invalida(self):
        with pytest.raises(ValueError) as exc:
            UrlValue(url="exemplo.com/pagina")
        assert "inválida" in str(exc.value).lower() or "invalida" in str(exc.value).lower()

    def test_url_vazia_invalida(self):
        with pytest.raises(ValueError):
            UrlValue(url="")

    def test_url_apenas_texto_invalida(self):
        with pytest.raises(ValueError):
            UrlValue(url="isso nao e uma url")

    def test_url_ftp_invalida(self):
        with pytest.raises(ValueError):
            UrlValue(url="ftp://arquivos.com")

    def test_url_https_sem_dominio_invalida(self):
        with pytest.raises(ValueError):
            UrlValue(url="https://")

    def test_url_imutavel(self):
        url = UrlValue(url="https://exemplo.com")
        with pytest.raises(Exception):
            url.value = "https://outro.com"
