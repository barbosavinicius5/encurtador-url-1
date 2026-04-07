"""Testes unitários para detecção de URL duplicada no ShortenUrlUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.application.dtos.shorten_url_dto import ShortenUrlRequest, ShortenUrlResponse
from app.application.use_cases.shorten_url_use_case import ShortenUrlUseCase
from app.domain.entities.shortened_url import ShortenedUrl


class TestDuplicateUrlDetection:
    """Testes para detecção de URL já encurtada no use case."""

    @pytest.fixture
    def mock_repository(self):
        repo = AsyncMock()
        repo.exists_by_short_code = AsyncMock(return_value=False)
        repo.save = AsyncMock(side_effect=lambda entity: entity)
        repo.find_by_original_url_and_session = AsyncMock(return_value=None)
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
    async def test_url_duplicada_mesma_sessao_retorna_409(self, use_case, mock_repository):
        """Cenário C: URL já encurtada para a mesma sessão deve retornar HTTP 409."""
        existing_link = ShortenedUrl(
            original_url="https://www.exemplo.com/longa",
            short_code="aB12x",
            session_id="sess-abc",
        )
        mock_repository.find_by_original_url_and_session = AsyncMock(return_value=existing_link)

        request = ShortenUrlRequest(url="https://www.exemplo.com/longa")

        with pytest.raises(HTTPException) as exc_info:
            await use_case.execute(request, session_id="sess-abc")

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["detail"] == "URL já encurtada"
        assert exc_info.value.detail["short_url"] == "aB12x"

    @pytest.mark.asyncio
    async def test_url_nova_mesma_sessao_cria_normalmente(self, use_case, mock_repository):
        """Cenário D: URL nova deve seguir fluxo normal e retornar HTTP 201."""
        mock_repository.find_by_original_url_and_session = AsyncMock(return_value=None)

        request = ShortenUrlRequest(url="https://www.exemplo.com/nova")
        response = await use_case.execute(request, session_id="sess-abc")

        assert isinstance(response, ShortenUrlResponse)
        assert response.original_url == "https://www.exemplo.com/nova"
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_url_duplicada_normalizacao_case_insensitive(self, use_case, mock_repository):
        """Cenário E: URL com capitalização diferente deve ser detectada como duplicata."""
        existing_link = ShortenedUrl(
            original_url="https://www.exemplo.com/longa",
            short_code="aB12x",
            session_id="sess-abc",
        )
        mock_repository.find_by_original_url_and_session = AsyncMock(return_value=existing_link)

        # URL em maiúsculas deve ser normalizada e detectada como duplicata
        request = ShortenUrlRequest(url="HTTPS://WWW.EXEMPLO.COM/LONGA")

        with pytest.raises(HTTPException) as exc_info:
            await use_case.execute(request, session_id="sess-abc")

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_repositorio_consultado_com_url_normalizada(self, use_case, mock_repository):
        """A URL passada para busca no repositório deve estar normalizada (lowercase)."""
        mock_repository.find_by_original_url_and_session = AsyncMock(return_value=None)

        request = ShortenUrlRequest(url="https://EXEMPLO.COM/PAGINA")
        await use_case.execute(request, session_id="sess-xyz")

        # O repositório deve ser chamado com URL normalizada (lowercase)
        mock_repository.find_by_original_url_and_session.assert_called_once()
        call_args = mock_repository.find_by_original_url_and_session.call_args
        url_passada = call_args.kwargs.get("original_url") or call_args.args[0]
        assert url_passada == url_passada.lower(), (
            f"URL deve estar em lowercase, mas foi: {url_passada}"
        )

    @pytest.mark.asyncio
    async def test_url_duplicada_sessao_diferente_cria_normalmente(self, use_case, mock_repository):
        """URL duplicada em sessão diferente deve criar novo link (sem 409)."""
        mock_repository.find_by_original_url_and_session = AsyncMock(return_value=None)

        request = ShortenUrlRequest(url="https://www.exemplo.com/longa")
        response = await use_case.execute(request, session_id="outra-sessao")

        assert isinstance(response, ShortenUrlResponse)
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_url_duplicada_sem_session_id_nao_levanta_409(self, use_case, mock_repository):
        """URL sem session_id não deve levantar 409 (usuário anônimo sem sessão)."""
        mock_repository.find_by_original_url_and_session = AsyncMock(return_value=None)

        request = ShortenUrlRequest(url="https://www.exemplo.com/longa")
        response = await use_case.execute(request, session_id=None)

        assert isinstance(response, ShortenUrlResponse)

    @pytest.mark.asyncio
    async def test_409_contém_short_url_do_link_existente(self, use_case, mock_repository):
        """O campo short_url no 409 deve conter o short_code do link existente."""
        existing_link = ShortenedUrl(
            original_url="https://exemplo.com/link",
            short_code="xyz789",
            session_id="sess-def",
        )
        mock_repository.find_by_original_url_and_session = AsyncMock(return_value=existing_link)

        request = ShortenUrlRequest(url="https://exemplo.com/link")

        with pytest.raises(HTTPException) as exc_info:
            await use_case.execute(request, session_id="sess-def")

        detail = exc_info.value.detail
        assert detail["short_url"] == "xyz789"
