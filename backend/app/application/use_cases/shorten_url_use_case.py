"""Use case para encurtamento de URL."""

import logging
import secrets
import string

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

    async def execute(self, request: ShortenUrlRequest) -> ShortenUrlResponse:
        """Encurta uma URL e retorna o link curto.

        Args:
            request: DTO com a URL a ser encurtada.

        Returns:
            DTO com short_code, short_url e original_url.

        Raises:
            ValueError: Se a URL for inválida.
            RuntimeError: Se não conseguir gerar short_code único.
        """
        # Valida URL via value object (lança ValueError se inválida)
        url = UrlValue(value=request.url)

        # Gera short_code único com retry
        short_code = await self._generate_unique_code()

        # Persiste
        entity = ShortenedUrl(original_url=url.value, short_code=short_code)
        saved = await self.repository.save(entity)

        return ShortenUrlResponse(
            short_code=saved.short_code,
            short_url=f"{self.settings.base_url}/{saved.short_code}",
            original_url=saved.original_url,
        )

    async def _generate_unique_code(
        self, length: int = 6, max_attempts: int = 5
    ) -> str:
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
