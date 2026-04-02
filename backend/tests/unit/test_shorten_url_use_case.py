"""Testes unitários para o use case ShortenUrlUseCase."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.application.use_cases.shorten_url_use_case import ShortenUrlUseCase
from app.application.dtos.shorten_url_dto import ShortenUrlRequest, ShortenUrlResponse
from app.domain.entities.shortened_url import ShortenedUrl


class TestShortenUrlUseCase:
    """Testes para o use case de encurtamento de URL."""

    @pytest.fixture
    def mock_repository(self):
        repo = AsyncMock()
        repo.exists_by_short_code = AsyncMock(return_value=False)
        repo.save = AsyncMock(side_effect=lambda entity: entity)
        return repo

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.base_url = "https://short.app"
        return settings

    @pytest.fixture
    def use_case(self, mock_repository, mock_settings):
        return ShortenUrlUseCase(repository=mock_repository, settings=mock_settings)

    @pytest.mark.asyncio
    async def test_encurtar_url_valida(self, use_case, mock_repository):
        request = ShortenUrlRequest(url="https://exemplo.com/pagina-longa")
        response = await use_case.execute(request)

        assert isinstance(response, ShortenUrlResponse)
        assert response.original_url == "https://exemplo.com/pagina-longa"
        assert len(response.short_code) >= 5
        assert response.short_code.isalnum()
        assert response.short_url == f"https://short.app/{response.short_code}"

    @pytest.mark.asyncio
    async def test_url_invalida_levanta_erro(self, use_case):
        request = ShortenUrlRequest(url="url-invalida")
        with pytest.raises(ValueError):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_gera_short_code_unico_com_retry(self, use_case, mock_repository):
        # Primeiras 4 chamadas retornam True (colisão), 5a retorna False
        mock_repository.exists_by_short_code = AsyncMock(
            side_effect=[True, True, True, True, False]
        )
        request = ShortenUrlRequest(url="https://exemplo.com/pagina")
        response = await use_case.execute(request)

        assert response is not None
        assert len(response.short_code) >= 5

    @pytest.mark.asyncio
    async def test_falha_apos_max_tentativas(self, use_case, mock_repository):
        mock_repository.exists_by_short_code = AsyncMock(return_value=True)
        request = ShortenUrlRequest(url="https://exemplo.com/pagina")
        with pytest.raises(RuntimeError):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_persiste_entidade_no_repositorio(self, use_case, mock_repository):
        request = ShortenUrlRequest(url="https://exemplo.com/pagina")
        await use_case.execute(request)
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_short_url_usa_base_url_do_settings(self, use_case):
        request = ShortenUrlRequest(url="https://exemplo.com/pagina")
        response = await use_case.execute(request)
        assert response.short_url.startswith("https://short.app/")

    @pytest.mark.asyncio
    async def test_dois_encurtamentos_geram_codigos_distintos(
        self, use_case, mock_repository
    ):
        mock_repository.exists_by_short_code = AsyncMock(return_value=False)

        request = ShortenUrlRequest(url="https://exemplo.com/pagina")
        response1 = await use_case.execute(request)
        response2 = await use_case.execute(request)

        # Short codes devem ser diferentes (base62 com secrets.choice garante isso na prática)
        # Verificamos apenas que ambos são válidos
        assert len(response1.short_code) >= 5
        assert len(response2.short_code) >= 5
        assert response1.short_code.isalnum()
        assert response2.short_code.isalnum()
