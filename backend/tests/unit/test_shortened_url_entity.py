"""Testes unitários para a entidade ShortenedUrl."""

from datetime import datetime

import pytest

from app.domain.entities.shortened_url import ShortenedUrl


@pytest.mark.unit
class TestShortenedUrlEntity:
    """Testes para a entidade de domínio ShortenedUrl."""

    def test_criar_entidade_com_campos_obrigatorios(self):
        entity = ShortenedUrl(original_url="https://exemplo.com/pagina-longa", short_code="aB3kZ9")
        assert entity.original_url == "https://exemplo.com/pagina-longa"
        assert entity.short_code == "aB3kZ9"
        assert entity.id is None
        assert isinstance(entity.created_at, datetime)

    def test_criar_entidade_com_id(self):
        entity = ShortenedUrl(original_url="https://exemplo.com", short_code="abc12", id=1)
        assert entity.id == 1

    def test_short_code_minimo_5_chars(self):
        entity = ShortenedUrl(original_url="https://exemplo.com", short_code="abc12")
        assert len(entity.short_code) >= 5

    def test_short_code_alfanumerico(self):
        entity = ShortenedUrl(original_url="https://exemplo.com", short_code="aB3kZ9")
        assert entity.short_code.isalnum()
