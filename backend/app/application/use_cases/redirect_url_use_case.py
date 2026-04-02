"""Use case para redirect de short_code para URL original."""

import asyncio
import logging

from app.domain.ports.url_repository_port import UrlRepositoryPort
from app.infrastructure.cache.redis_client import RedisClient

logger = logging.getLogger(__name__)


class RedirectUrlUseCase:
    """Use case responsável por resolver o redirect de um short_code."""

    def __init__(self, repository: UrlRepositoryPort, cache: RedisClient):
        self.repository = repository
        self.cache = cache

    async def execute(self, short_code: str) -> str:
        """Retorna a URL original para um short_code.

        Tenta o cache Redis primeiro; se não encontrar, busca no banco
        e popula o cache. Registra o clique de forma assíncrona (fire-and-forget)
        via Redis sem bloquear o redirect.

        Args:
            short_code: Código do link encurtado.

        Returns:
            URL original.

        Raises:
            ValueError: Se o short_code não for encontrado.
        """
        cache_key = f"url:{short_code}"

        # Cache hit
        try:
            cached_url = await self.cache.get(cache_key)
            if cached_url:
                logger.info(
                    "Redirect via cache Redis",
                    extra={"short_code": short_code, "cache_hit": True},
                )
                # Fire-and-forget: registrar clique de forma assíncrona
                asyncio.create_task(self._register_click_async(short_code))
                return cached_url
        except Exception as e:
            logger.warning(
                "Erro ao consultar cache Redis — fallback para banco",
                extra={"short_code": short_code, "error": str(e)},
            )

        # Cache miss: busca no banco
        entity = await self.repository.find_by_short_code(short_code)
        if not entity:
            raise ValueError(f"short_code '{short_code}' não encontrado")

        # Popula cache
        try:
            await self.cache.set(cache_key, entity.original_url, ttl_seconds=3600)
        except Exception as e:
            logger.warning(
                "Erro ao popular cache Redis",
                extra={"short_code": short_code, "error": str(e)},
            )

        logger.info(
            "Redirect via banco de dados",
            extra={"short_code": short_code, "cache_hit": False},
        )

        # Fire-and-forget: registrar clique de forma assíncrona
        asyncio.create_task(self._register_click_async(short_code))

        return entity.original_url

    async def _register_click_async(self, short_code: str) -> None:
        """Registra um clique de forma assíncrona via Redis.

        Falhas são silenciadas e logadas como WARNING — não devem
        impactar o redirect principal.

        Args:
            short_code: Código do link encurtado que recebeu o clique.
        """
        try:
            await self.cache.increment_with_ttl(f"clicks:{short_code}", ttl_seconds=3600)
        except Exception as e:
            logger.warning(
                "Falha ao registrar clique no Redis",
                extra={"short_code": short_code, "error": str(e)},
            )

    async def _persist_click(self, short_code: str) -> None:
        """Persiste o clique no banco de dados.

        Falhas são silenciadas e logadas como ERROR — não devem
        impactar o redirect principal.

        Args:
            short_code: Código do link encurtado que recebeu o clique.
        """
        try:
            await self.repository.increment_click_count(short_code)
        except Exception as e:
            logger.error(
                "Falha ao persistir clique no banco",
                extra={"short_code": short_code, "error": str(e)},
            )
