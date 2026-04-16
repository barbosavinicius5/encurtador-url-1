"""Testes unitários para o value object UrlValue."""

import pytest

from app.domain.value_objects.url import UrlValue


class TestUrlValueObject:
    """Testes para validação de URL."""

    def test_url_valida_http(self):
        url = UrlValue(value="http://exemplo.com")
        assert url.value == "http://exemplo.com"

    def test_url_valida_https(self):
        url = UrlValue(value="https://exemplo.com/pagina-longa")
        assert url.value == "https://exemplo.com/pagina-longa"

    def test_url_valida_com_path(self):
        url = UrlValue(value="https://www.exemplo.com/artigo/como-usar?q=teste")
        assert url.value == "https://www.exemplo.com/artigo/como-usar?q=teste"

    def test_url_valida_localhost(self):
        url = UrlValue(value="http://localhost:8000/api")
        assert url.value == "http://localhost:8000/api"

    def test_url_sem_protocolo_invalida(self):
        with pytest.raises(ValueError) as exc:
            UrlValue(value="exemplo.com/pagina")
        assert "inválida" in str(exc.value).lower() or "invalida" in str(exc.value).lower()

    def test_url_vazia_invalida(self):
        with pytest.raises(ValueError):
            UrlValue(value="")

    def test_url_apenas_texto_invalida(self):
        with pytest.raises(ValueError):
            UrlValue(value="isso nao e uma url")

    def test_url_ftp_invalida(self):
        with pytest.raises(ValueError):
            UrlValue(value="ftp://arquivos.com")

    def test_url_https_sem_dominio_invalida(self):
        with pytest.raises(ValueError):
            UrlValue(value="https://")

    def test_url_imutavel(self):
        url = UrlValue(value="https://exemplo.com")
        with pytest.raises(Exception):
            url.value = "https://outro.com"


class TestUrlValueObjectUrlsValidasNaoConvencionais:
    """Testes para URLs válidas não convencionais — Cenários A, B, C da spec."""

    @pytest.mark.parametrize(
        "url",
        [
            # Cenário A: percent-encoding no path
            "https://exemplo.com/path%20com%20espacos",
            "https://exemplo.com/produtos/categoria%20especial",
            "https://exemplo.com/resource%2Fencoded",
            # Cenário B: query string complexa com + e percent-encoding
            "https://exemplo.com/search?q=hello+world",
            "https://exemplo.com/search?filter=a%26b",
            "https://exemplo.com/search?q=hello+world&filter=a%26b",
            "https://exemplo.com/path?param1=value1&param2=value2&param3=value%20encoded",
            # Cenário C: fragmentos (#)
            "https://exemplo.com/page#section-1",
            "https://exemplo.com/page?q=1#top",
            "https://exemplo.com/#anchor",
            "https://exemplo.com/path?q=test#section",
            # Outros casos válidos menos comuns
            "http://sub.exemplo.com.br/path/to/resource",
            "https://a.b.c.d.e.f.exemplo.com.br/very/long/path",
            "https://exemplo.com:8080/api/v1/resource",
        ],
    )
    def test_url_value_aceita_urls_validas_nao_convencionais(self, url):
        """URLs válidas não convencionais devem ser aceitas sem exceção."""
        vo = UrlValue(value=url)
        assert vo.value == url


class TestUrlValueObjectUrlsInvalidasSeguranca:
    """Testes para URLs inválidas — Cenários D, E, F da spec."""

    @pytest.mark.parametrize(
        "url",
        [
            # Cenário D: esquemas perigosos (XSS/injection)
            "javascript:alert(1)",
            "javascript:void(0)",
            "JAVASCRIPT:alert(1)",
            "Javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "data:text/html;base64,PHNjcmlwdD4=",
            "vbscript:msgbox(1)",
            # Cenário E: esquemas não HTTP/HTTPS
            "ftp://exemplo.com/file",
            "sftp://exemplo.com/file",
            "file:///etc/passwd",
            "//exemplo.com",
            # Cenário F: vazio ou apenas espaços
            "",
            "   ",
            # Outros inválidos
            "not-a-url",
            "http://",
            "https://",
        ],
    )
    def test_url_value_rejeita_urls_invalidas(self, url):
        """URLs inválidas ou com esquemas perigosos devem lançar exceção."""
        with pytest.raises((ValueError, Exception)):
            UrlValue(value=url)
