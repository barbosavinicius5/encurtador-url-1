"""Use case para consulta de detalhes de uma URL encurtada."""

import logging

from app.application.dtos.get_url_details_dto import GetUrlDetailsResponse
from app.domain.ports.url_repository_port import UrlRepositoryPort

logger = logging.getLogger(__name__)


class UrlNotFoundError(Exception):
    """Levantado quando o short_code não é encontrado."""

    def __init__(self, short_code: str):
        self.short_code = short_code
        super().__init__(f"URL com short_code '{short_code}' não encontrada")


class GetUrlDetailsUseCase:
    """Use case para consultar detalhes de uma URL encurtada.

    Retorna a URL original, short_code, URL completa e contagem de cliques.
    """

    def __init__(self, repository: UrlRepositoryPort, base_url: str):
        """Inicializa o use case.

        Args:
            repository: Repositório de URLs.
            base_url: URL base para construir a short_url completa (ex: https://short.app).
        """
        self.repository = repository
        self.base_url = base_url.rstrip("/")

    async def execute(self, short_code: str) -> GetUrlDetailsResponse:
        """Consulta detalhes de uma URL encurtada.

        Args:
            short_code: Código único da URL encurtada.

        Returns:
            GetUrlDetailsResponse com detalhes da URL.

        Raises:
            UrlNotFoundError: Se o short_code não for encontrado.
        """
        logger.info("Consultando detalhes da URL", extra={"short_code": short_code})

        url = await self.repository.find_by_short_code(short_code)
        if not url:
            logger.info("URL não encontrada", extra={"short_code": short_code})
            raise UrlNotFoundError(short_code)

        short_url = f"{self.base_url}/{url.short_code}"

        logger.info(
            "Detalhes da URL consultados",
            extra={"short_code": short_code, "click_count": url.click_count},
        )

        return GetUrlDetailsResponse(
            original_url=url.original_url,
            short_code=url.short_code,
            short_url=short_url,
            click_count=url.click_count,
        )
