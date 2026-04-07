"""Testes unitários para a camada de sanitização de inputs."""

import pytest

from app.domain.exceptions import InvalidUrlError
from app.domain.sanitization import sanitize_slug, sanitize_url


class TestSanitizeUrl:
    """Testes para a função sanitize_url."""

    def test_url_com_espacos_nas_extremidades_e_sanitizada(self):
        result = sanitize_url("  https://exemplo.com  ")
        assert result == "https://exemplo.com"

    def test_url_sem_espacos_nao_e_alterada(self):
        result = sanitize_url("https://exemplo.com")
        assert result == "https://exemplo.com"

    def test_url_com_scheme_uppercase_e_normalizada(self):
        result = sanitize_url("HTTPS://exemplo.com/path")
        assert result == "https://exemplo.com/path"

    def test_url_com_scheme_mixed_case_e_normalizada(self):
        result = sanitize_url("Http://exemplo.com")
        assert result == "http://exemplo.com"

    def test_url_com_caracter_de_controle_e_sanitizada(self):
        result = sanitize_url("https://exemplo.com\x00/path")
        assert "\x00" not in result
        assert result == "https://exemplo.com/path"

    def test_url_com_multiplos_caracteres_de_controle(self):
        result = sanitize_url("https://\x01exemplo\x02.com\x03")
        assert "\x01" not in result
        assert "\x02" not in result
        assert "\x03" not in result

    def test_url_acima_de_2048_chars_lanca_invalid_url_error(self):
        url = "https://exemplo.com/" + "a" * 2040
        assert len(url) > 2048
        with pytest.raises(InvalidUrlError) as exc:
            sanitize_url(url)
        assert "2048" in exc.value.reason

    def test_url_com_exatamente_2048_chars_e_aceita(self):
        # Exatamente 2048 chars deve ser aceito
        url = "https://exemplo.com/" + "a" * (2048 - len("https://exemplo.com/"))
        assert len(url) == 2048
        result = sanitize_url(url)
        assert len(result) == 2048

    def test_url_valida_retorna_string(self):
        result = sanitize_url("https://exemplo.com")
        assert isinstance(result, str)

    def test_url_com_path_nao_e_alterada(self):
        result = sanitize_url("https://exemplo.com/path?q=1&foo=bar")
        assert result == "https://exemplo.com/path?q=1&foo=bar"


class TestSanitizeSlug:
    """Testes para a função sanitize_slug."""

    def test_slug_com_espacos_nas_extremidades_e_sanitizado(self):
        result = sanitize_slug("  MinhaURL  ")
        assert result == "minhaurl"

    def test_slug_convertido_para_lowercase(self):
        result = sanitize_slug("MinhaURL-Custom")
        assert result == "minhaurl-custom"

    def test_slug_com_caracteres_especiais_removidos(self):
        result = sanitize_slug("  MinhaURL-Custom!@#  ")
        assert result == "minhaurl-custom"

    def test_slug_alfanumerico_mantido(self):
        result = sanitize_slug("abc123")
        assert result == "abc123"

    def test_slug_com_hifen_mantido(self):
        result = sanitize_slug("meu-slug")
        assert result == "meu-slug"

    def test_slug_com_underscore_mantido(self):
        result = sanitize_slug("meu_slug")
        assert result == "meu_slug"

    def test_slug_acima_de_50_chars_lanca_invalid_url_error(self):
        slug = "a" * 51
        with pytest.raises(InvalidUrlError) as exc:
            sanitize_slug(slug)
        assert "50" in exc.value.reason

    def test_slug_com_exatamente_50_chars_e_aceito(self):
        slug = "a" * 50
        result = sanitize_slug(slug)
        assert len(result) == 50

    def test_slug_retorna_string(self):
        result = sanitize_slug("meuslug")
        assert isinstance(result, str)

    def test_slug_com_apenas_caracteres_especiais_retorna_vazio(self):
        result = sanitize_slug("!@#$%^&*()")
        assert result == ""
