"""Testes unitários para os value objects de Project."""

import pytest

from app.domain.value_objects.project_description import ProjectDescription
from app.domain.value_objects.project_name import ProjectName


class TestProjectName:
    """Testes para o value object ProjectName."""

    def test_valid_name(self):
        name = ProjectName("Meu Projeto")
        assert name.value == "Meu Projeto"

    def test_minimum_length(self):
        name = ProjectName("abc")
        assert name.value == "abc"

    def test_maximum_length(self):
        name = ProjectName("a" * 100)
        assert len(name.value) == 100

    def test_strips_whitespace(self):
        name = ProjectName("  Projeto  ")
        assert name.value == "Projeto"

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="3"):
            ProjectName("ab")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            ProjectName("")

    def test_only_spaces_raises(self):
        with pytest.raises(ValueError):
            ProjectName("   ")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="100"):
            ProjectName("a" * 101)

    def test_exactly_3_chars_valid(self):
        name = ProjectName("abc")
        assert name.value == "abc"

    def test_str_representation(self):
        name = ProjectName("Meu Projeto")
        assert str(name) == "Meu Projeto"

    def test_immutable(self):
        name = ProjectName("Projeto")
        with pytest.raises((AttributeError, TypeError)):
            name.value = "Outro"  # type: ignore


class TestProjectDescription:
    """Testes para o value object ProjectDescription."""

    def test_valid_description(self):
        desc = ProjectDescription("Uma descrição válida")
        assert desc.value == "Uma descrição válida"

    def test_none_is_valid(self):
        desc = ProjectDescription(None)
        assert desc.value is None

    def test_empty_string_is_valid(self):
        desc = ProjectDescription("")
        assert desc.value == ""

    def test_maximum_length(self):
        desc = ProjectDescription("a" * 500)
        assert len(desc.value) == 500

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="500"):
            ProjectDescription("a" * 501)

    def test_str_none_returns_empty(self):
        desc = ProjectDescription(None)
        assert str(desc) == ""

    def test_str_value(self):
        desc = ProjectDescription("descrição")
        assert str(desc) == "descrição"
