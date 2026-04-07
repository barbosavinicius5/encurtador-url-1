"""Adapter PostgreSQL para o repositório de URLs."""

import logging
from typing import Optional

from sqlalchemy import asc, select, update
from sqlalchemy import desc as sa_desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.shortened_url import ShortenedUrl
from app.domain.ports.url_repository_port import UrlRepositoryPort
from app.infrastructure.db.models import ShortenedUrlModel

logger = logging.getLogger(__name__)


class PostgreSQLUrlRepository(UrlRepositoryPort):
    """Implementação do repositório usando PostgreSQL via SQLAlchemy async."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, shortened_url: ShortenedUrl) -> ShortenedUrl:
        """Persiste uma URL encurtada no banco de dados.

        Args:
            shortened_url: Entidade a ser persistida.

        Returns:
            Entidade com ID gerado pelo banco.
        """
        model = ShortenedUrlModel(
            original_url=shortened_url.original_url,
            short_code=shortened_url.short_code,
            session_id=shortened_url.session_id,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

        logger.info(
            "URL encurtada persistida",
            extra={"short_code": model.short_code, "id": model.id},
        )

        return ShortenedUrl(
            original_url=model.original_url,
            short_code=model.short_code,
            created_at=model.created_at,
            id=model.id,
            session_id=model.session_id,
        )

    async def find_by_short_code(self, short_code: str) -> ShortenedUrl | None:
        """Busca uma URL pelo short_code.

        Args:
            short_code: Código único da URL encurtada.

        Returns:
            Entidade se encontrada, None caso contrário.
            Retorna None se deleted_at não for None (soft delete).
        """
        stmt = select(ShortenedUrlModel).where(
            ShortenedUrlModel.short_code == short_code,
            ShortenedUrlModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return ShortenedUrl(
            original_url=model.original_url,
            short_code=model.short_code,
            created_at=model.created_at,
            id=model.id,
            click_count=model.click_count if model.click_count is not None else 0,
            deleted_at=model.deleted_at,
        )

    async def exists_by_short_code(self, short_code: str) -> bool:
        """Verifica se um short_code já existe no banco.

        Args:
            short_code: Código a verificar.

        Returns:
            True se existir, False caso contrário.
        """
        stmt = select(ShortenedUrlModel.id).where(ShortenedUrlModel.short_code == short_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def increment_click_count(self, short_code: str) -> None:
        """Incrementa o contador de cliques para um short_code.

        Args:
            short_code: Código único da URL encurtada.
        """
        stmt = (
            update(ShortenedUrlModel)
            .where(ShortenedUrlModel.short_code == short_code)
            .values(click_count=ShortenedUrlModel.click_count + 1)
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(
            "Click count incrementado",
            extra={"short_code": short_code},
        )

    async def find_by_session_id(
        self,
        session_id: str,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[ShortenedUrl]:
        """Retorna todos os links associados ao session_id.

        Args:
            session_id: UUID da sessão anônima.
            sort_by: Campo de ordenação. Valores aceitos: 'created_at', 'click_count'.
                     Default: 'created_at'.
            sort_order: Direção da ordenação. Valores aceitos: 'asc', 'desc'.
                        Default: 'desc'.

        Returns:
            Lista de entidades ordenadas conforme os parâmetros.
        """
        sort_column = getattr(ShortenedUrlModel, sort_by)
        order_fn = sa_desc if sort_order == "desc" else asc

        stmt = (
            select(ShortenedUrlModel)
            .where(
                ShortenedUrlModel.session_id == session_id,
                ShortenedUrlModel.deleted_at.is_(None),
            )
            .order_by(order_fn(sort_column))
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [
            ShortenedUrl(
                original_url=model.original_url,
                short_code=model.short_code,
                created_at=model.created_at,
                id=model.id,
                click_count=model.click_count if model.click_count is not None else 0,
                deleted_at=model.deleted_at,
                session_id=model.session_id,
            )
            for model in models
        ]

    async def find_by_original_url_and_session(
        self,
        original_url: str,
        session_id: str,
    ) -> Optional[ShortenedUrl]:
        """Retorna o link se já existir para essa URL + sessão, None caso contrário.

        Args:
            original_url: URL original já normalizada (lowercase, sem espaços extras).
            session_id: UUID da sessão anônima.

        Returns:
            Entidade ShortenedUrl se encontrada, None caso contrário.
        """
        stmt = select(ShortenedUrlModel).where(
            ShortenedUrlModel.original_url == original_url,
            ShortenedUrlModel.session_id == session_id,
            ShortenedUrlModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return ShortenedUrl(
            original_url=model.original_url,
            short_code=model.short_code,
            created_at=model.created_at,
            id=model.id,
            click_count=model.click_count if model.click_count is not None else 0,
            deleted_at=model.deleted_at,
            session_id=model.session_id,
        )
