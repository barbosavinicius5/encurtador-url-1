"""FastAPI dependency para autenticação por API Key."""

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.domain.entities.api_key import ApiKey
from app.infrastructure.db.repositories.api_key_repository import PostgreSQLApiKeyRepository
from app.infrastructure.db.session import get_session
from app.infrastructure.middleware.rate_limiter import rate_limit_by_api_key

logger = logging.getLogger(__name__)


async def get_api_key_repository(
    session: AsyncSession = Depends(get_session),
) -> PostgreSQLApiKeyRepository:
    """Dependency que fornece o repositório de API Keys."""
    return PostgreSQLApiKeyRepository(session)


async def api_key_auth(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    repo: PostgreSQLApiKeyRepository = Depends(get_api_key_repository),
    settings: Settings = Depends(get_settings),
) -> ApiKey:
    """FastAPI dependency que valida autenticação por API Key.

    Extrai o header X-API-Key, valida no repositório e aplica rate limiting.
    Rejeita com 401 se a chave estiver ausente ou inválida/inativa.
    Rejeita com 429 se o limite de requisições por minuto for excedido.

    Args:
        x_api_key: Valor do header X-API-Key.
        repo: Repositório de API Keys.
        settings: Configurações da aplicação.

    Returns:
        Entidade ApiKey válida e ativa.

    Raises:
        HTTPException 401: Se a chave estiver ausente ou inválida/inativa.
        HTTPException 429: Se o rate limit for excedido.
    """
    if not x_api_key:
        logger.warning("Requisição sem header X-API-Key")
        raise HTTPException(
            status_code=401,
            detail={
                "error_type": "UNAUTHORIZED",
                "message": "API key ausente ou inválida.",
            },
        )

    # Log com prefixo apenas — nunca o valor completo
    key_prefix = x_api_key[:8] if len(x_api_key) >= 8 else x_api_key
    logger.info("Validando API Key", extra={"key_prefix": key_prefix})

    api_key = await repo.get_by_key(x_api_key)

    if not api_key or not api_key.is_active:
        logger.warning(
            "API Key inválida ou inativa",
            extra={"key_prefix": key_prefix},
        )
        raise HTTPException(
            status_code=401,
            detail={
                "error_type": "UNAUTHORIZED",
                "message": "API key ausente ou inválida.",
            },
        )

    # Aplicar rate limiting por API Key
    await rate_limit_by_api_key(x_api_key, settings)

    return api_key
