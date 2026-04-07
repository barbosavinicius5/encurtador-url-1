"""Adapter PostgreSQL para o repositório de API Keys."""

import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.api_key import ApiKey
from app.domain.ports.api_key_repository_port import ApiKeyRepositoryPort
from app.infrastructure.db.models import ApiKeyModel

logger = logging.getLogger(__name__)


class PostgreSQLApiKeyRepository(ApiKeyRepositoryPort):
    """Implementação do repositório de API Keys usando PostgreSQL via SQLAlchemy async."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_key(self, key: str) -> Optional[ApiKey]:
        """Busca uma API Key pelo valor da chave.

        Args:
            key: Valor da chave de API.

        Returns:
            Entidade ApiKey se encontrada, None caso contrário.
        """
        stmt = select(ApiKeyModel).where(ApiKeyModel.key == key)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return ApiKey(
            id=model.id,
            key=model.key,
            owner=model.owner,
            is_active=model.is_active,
            created_at=model.created_at,
        )

    async def save(self, api_key: ApiKey) -> ApiKey:
        """Persiste uma API Key no banco de dados.

        Args:
            api_key: Entidade a ser persistida.

        Returns:
            Entidade com ID gerado pelo banco.
        """
        model = ApiKeyModel(
            id=api_key.id or str(uuid.uuid4()),
            key=api_key.key,
            owner=api_key.owner,
            is_active=api_key.is_active,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

        logger.info(
            "API Key persistida",
            extra={"owner": model.owner, "key_prefix": model.key[:8]},
        )

        return ApiKey(
            id=model.id,
            key=model.key,
            owner=model.owner,
            is_active=model.is_active,
            created_at=model.created_at,
        )
