"""Testes unitários para o GetUrlDetailsUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.get_url_details_use_case import (
    GetUrlDetailsUseCase,
    UrlNotFoundError,
)
from app.domain.entities.shortened_url import ShortenedUrl


@pytest.mark.unit
class TestGetUrlDetailsUseCase:
    """Testes para o use case de consulta de detalhes de URL."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_repository):
        return GetUrlDetailsUseCase(
            repository=mock_repository,
            base_url="https://short.app",
        )

    @pytest.mark.asyncio
    async def test_retorna_detalhes_url_existente(self, use_case, mock_repository):
        """Deve retornar detalhes quando a URL existe."""
        mock_repository.find_by_short_code.return_value = ShortenedUrl(
            original_url="https://www.exemplo.com/pagina",
            short_code="abc123",
            click_count=5,
            created_at=datetime.now(UTC),
        )

        result = await use_case.execute("abc123")

        assert result.original_url == "https://www.exemplo.com/pagina"
        assert result.short_code == "abc123"
        assert result.short_url == "https://short.app/abc123"
        assert result.click_count == 5

    @pytest.mark.asyncio
    async def test_levanta_url_not_found_error_para_short_code_inexistente(
        self, use_case, mock_repository
    ):
        """Deve levantar UrlNotFoundError quando short_code não existe."""
        mock_repository.find_by_short_code.return_value = None

        with pytest.raises(UrlNotFoundError) as exc_info:
            await use_case.execute("nao-existe")

        assert "nao-existe" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_short_url_usa_base_url_configurado(self, mock_repository):
        """short_url deve usar o base_url configurado."""
        mock_repository.find_by_short_code.return_value = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="xyz789",
            click_count=0,
            created_at=datetime.now(UTC),
        )
        use_case = GetUrlDetailsUseCase(
            repository=mock_repository,
            base_url="https://shor.ty",
        )

        result = await use_case.execute("xyz789")

        assert result.short_url == "https://shor.ty/xyz789"

    @pytest.mark.asyncio
    async def test_base_url_com_barra_final_e_normalizado(self, mock_repository):
        """base_url com barra final deve ser normalizado."""
        mock_repository.find_by_short_code.return_value = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            click_count=0,
            created_at=datetime.now(UTC),
        )
        use_case = GetUrlDetailsUseCase(
            repository=mock_repository,
            base_url="https://short.app/",
        )

        result = await use_case.execute("abc123")

        assert result.short_url == "https://short.app/abc123"
        assert not result.short_url.startswith("https://short.app//")

    @pytest.mark.asyncio
    async def test_click_count_zero_para_url_nunca_acessada(self, use_case, mock_repository):
        """click_count deve ser 0 para URL sem cliques."""
        mock_repository.find_by_short_code.return_value = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            click_count=0,
            created_at=datetime.now(UTC),
        )

        result = await use_case.execute("abc123")

        assert result.click_count == 0

    @pytest.mark.asyncio
    async def test_click_count_reflete_valor_do_banco(self, use_case, mock_repository):
        """click_count deve refletir o valor persistido no banco."""
        mock_repository.find_by_short_code.return_value = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            click_count=42,
            created_at=datetime.now(UTC),
        )

        result = await use_case.execute("abc123")

        assert result.click_count == 42
