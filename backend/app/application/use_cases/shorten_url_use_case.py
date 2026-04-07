"""Use case para encurtamento de URL."""

import logging
import secrets
import string
from typing import Optional

from fastapi import HTTPException

from app.application.dtos.shorten_url_dto import ShortenUrlRequest, ShortenUrlResponse
from app.config import Settings
from app.domain.entities.shortened_url import ShortenedUrl
from app.domain.ports.url_repository_port import UrlRepositoryPort
from app.domain.value_objects.url import UrlValue

logger = logging.getLogger(__name__)

ALPHABET = string.ascii_letters + string.digits  # base62


class ShortenUrlUseCase:
    """Use case responsável por encurtar URLs."""

    def __init__(self, repository: UrlRepositoryPort, settings: Settings):
        self.repository = repository
        self.settings = settings

    async def execute(
        self, request: ShortenUrlRequest, session_id: Optional[str] = None
    ) -> ShortenUrlResponse:
        """Encurta uma URL e retorna o link curto.

        Args:
            request: DTO com a URL a ser encurtada.
            session_id: UUID da sessão anônima (opcional).

        Returns:
            DTO com short_code, short_url e original_url.

        Raises:
            ValueError: Se a URL for inválida.
            HTTPException(409): Se a URL já foi encurtada pela mesma sessão.
            RuntimeError: Se não conseguir gerar short_code único.
        """
        # Valida URL via value object (lança ValueError se inválida)
        url = UrlValue(value=request.url)

        # Normaliza a URL para comparação case-insensitive
        normalized_url = url.value.strip().lower()

        # Verifica duplicata por URL + sessão (apenas quando session_id está presente)
        if session_id:
            existing = await self.repository.find_by_original_url_and_session(
                original_url=normalized_url,
                session_id=session_id,
            )
            if existing:
                logger.info(
                    "URL já encurtada para a sessão, retornando link existente",
                    extra={"short_code": existing.short_code},
                )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "detail": "URL já encurtada",
                        "short_url": existing.short_code,
                    },
                )

        # Gera short_code único com retry
        short_code = await self._generate_unique_code()

        # Persiste com session_id e URL normalizada
        entity = ShortenedUrl(
            original_url=normalized_url,
            short_code=short_code,
            session_id=session_id,
        )
        saved = await self.repository.save(entity)

        return ShortenUrlResponse(
            short_code=saved.short_code,
            short_url=f"{self.settings.base_url}/{saved.short_code}",
            original_url=saved.original_url,
        )

    async def _generate_unique_code(self, length: int = 6, max_attempts: int = 5) -> str:
        """Gera um short_code único verificando colisões no banco.

        Args:
            length: Tamanho do código (mínimo 5).
            max_attempts: Máximo de tentativas antes de lançar RuntimeError.

        Returns:
            Short code único.

        Raises:
            RuntimeError: Se não conseguir gerar código único após max_attempts.
        """
        for attempt in range(max_attempts):
            code = "".join(secrets.choice(ALPHABET) for _ in range(length))
            if not await self.repository.exists_by_short_code(code):
                return code
            logger.warning(
                "Colisão de short_code detectada",
                extra={"attempt": attempt + 1, "max_attempts": max_attempts},
            )

        raise RuntimeError(
            f"Não foi possível gerar short_code único após {max_attempts} tentativas"
        )
