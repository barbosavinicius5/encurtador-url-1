"""Middleware de rate limiting por IP usando Redis."""

import logging

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings
from app.infrastructure.cache.redis_client import RedisClient

logger = logging.getLogger(__name__)


async def rate_limit_by_ip(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """FastAPI dependency que aplica rate limiting por IP.

    Implementa sliding window simplificado usando Redis INCR + EXPIRE.
    Comportamento fail-open: se Redis estiver indisponível, permite a requisição.

    Args:
        request: Requisição FastAPI com IP do cliente.
        settings: Configurações da aplicação.

    Raises:
        HTTPException 429: Se o IP ultrapassou o limite de requisições.
    """
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{client_ip}"

    try:
        redis_client = RedisClient(settings)
        count = await redis_client.increment_with_ttl(
            key,
            ttl_seconds=settings.rate_limit_window_seconds,
        )
        await redis_client.close()

        if count > settings.rate_limit_requests:
            logger.warning(
                "Rate limit atingido",
                extra={
                    "ip": client_ip,
                    "count": count,
                    "limit": settings.rate_limit_requests,
                },
            )
            raise HTTPException(
                status_code=429,
                detail="Limite de requisições atingido. Tente novamente em instantes.",
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )
    except HTTPException:
        raise
    except Exception as e:
        # Fail-open: se Redis estiver indisponível, permite a requisição
        logger.warning(
            "Redis indisponível no rate limiter — fail open",
            extra={"ip": client_ip, "error": str(e)},
        )
