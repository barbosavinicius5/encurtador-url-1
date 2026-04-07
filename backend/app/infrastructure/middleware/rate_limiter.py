"""Middleware de rate limiting por IP ou API Key usando Redis."""

import logging

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings
from app.infrastructure.cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

_BRUTE_FORCE_COUNT_KEY = "brute_force:count:{ip}"


async def rate_limit_by_ip(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """FastAPI dependency que aplica rate limiting por IP.

    Implementa sliding window simplificado usando Redis INCR + EXPIRE.
    Quando o limite é atingido, incrementa o contador de violações para
    detecção de força bruta pelo brute_force_protection dependency.

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

        if count > settings.rate_limit_requests:
            # Obter TTL real da chave para o header Retry-After
            ttl = await redis_client.get_ttl(key)
            retry_after = max(ttl, 1) if ttl > 0 else settings.rate_limit_window_seconds

            # Incrementar contador de violações para detecção de brute force
            count_key = _BRUTE_FORCE_COUNT_KEY.format(ip=client_ip)
            try:
                await redis_client.increment_with_ttl(
                    count_key,
                    ttl_seconds=settings.brute_force_detection_window_seconds,
                )
            except Exception:
                pass  # Não falhar o rate limiting por erro no counter de brute force

            logger.warning(
                "Rate limit atingido",
                extra={
                    "client_ip": client_ip,
                    "count": count,
                    "limit": settings.rate_limit_requests,
                    "endpoint": str(request.url.path),
                    "block_type": "rate_limit",
                    "retry_after": retry_after,
                },
            )
            raise HTTPException(
                status_code=429,
                detail="Limite de requisições atingido. Tente novamente em instantes.",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except Exception as e:
        # Fail-open: se Redis estiver indisponível, permite a requisição
        logger.warning(
            "Redis indisponível no rate limiter — fail open",
            extra={"client_ip": client_ip, "error": str(e)},
        )


async def rate_limit_by_api_key(
    api_key_value: str,
    settings: Settings,
) -> None:
    """Aplica rate limiting por API Key.

    Implementa sliding window simplificado usando Redis INCR + EXPIRE.
    Comportamento fail-open: se Redis estiver indisponível, permite a requisição.
    Limite de 60 req/min por API Key.

    Args:
        api_key_value: Valor da API Key extraído do header.
        settings: Configurações da aplicação.

    Raises:
        HTTPException 429: Se a API Key ultrapassou o limite de requisições.
    """
    # Usar prefixo da key para não expor o valor completo nos logs
    key_prefix = api_key_value[:8] if len(api_key_value) >= 8 else api_key_value
    redis_key = f"rate_limit:apikey:{api_key_value}"

    try:
        redis_client = RedisClient(settings)
        count = await redis_client.increment_with_ttl(
            redis_key,
            ttl_seconds=settings.rate_limit_window_seconds,
        )

        if count > settings.api_rate_limit_requests:
            ttl = await redis_client.get_ttl(redis_key)
            retry_after = max(ttl, 1) if ttl > 0 else settings.rate_limit_window_seconds

            logger.warning(
                "Rate limit por API Key atingido",
                extra={
                    "key_prefix": key_prefix,
                    "count": count,
                    "limit": settings.api_rate_limit_requests,
                },
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit excedido. Tente novamente em {retry_after} segundos.",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except Exception as e:
        # Fail-open: se Redis estiver indisponível, permite a requisição
        logger.warning(
            "Redis indisponível no rate limiter por API Key — fail open",
            extra={"key_prefix": key_prefix, "error": str(e)},
        )
