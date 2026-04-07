"""Middleware de detecção de força bruta com bloqueio progressivo via Redis.

Detecta padrões abusivos (força bruta / varredura) quando um IP ultrapassa
RATE_LIMIT_REQUESTS × BRUTE_FORCE_THRESHOLD_MULTIPLIER violações de rate limit
dentro da janela BRUTE_FORCE_DETECTION_WINDOW_SECONDS, aplicando bloqueio progressivo
por BRUTE_FORCE_BLOCK_SECONDS.

Chaves Redis utilizadas:
- brute_force:block:{ip}  — flag de bloqueio ativo (TTL = BRUTE_FORCE_BLOCK_SECONDS)
- brute_force:count:{ip}  — contador de violações na janela expandida
"""

import logging

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings
from app.infrastructure.cache.redis_client import RedisClient
from app.infrastructure.di.container import get_redis_client

logger = logging.getLogger(__name__)

_BRUTE_FORCE_BLOCK_KEY = "brute_force:block:{ip}"
_BRUTE_FORCE_COUNT_KEY = "brute_force:count:{ip}"


async def brute_force_protection(
    request: Request,
    settings: Settings = Depends(get_settings),
    redis: RedisClient = Depends(get_redis_client),
) -> None:
    """FastAPI dependency que detecta padrões abusivos e aplica bloqueio progressivo.

    Implementa dois níveis de proteção:
    1. Verifica se o IP já está bloqueado por detecção de brute force anterior.
    2. Incrementa o contador de violações na janela expandida e ativa bloqueio
       progressivo quando o threshold é atingido.

    Este dependency deve ser executado APÓS rate_limit_by_ip, pois o contador
    de violações é incrementado quando o IP já está sendo limitado.

    Comportamento fail-open: se Redis estiver indisponível, permite a requisição.

    Args:
        request: Requisição FastAPI com IP do cliente.
        settings: Configurações da aplicação.
        redis: Cliente Redis injetado.

    Raises:
        HTTPException 429: Se o IP estiver bloqueado por padrão abusivo detectado.
    """
    client_ip = request.client.host if request.client else "unknown"
    block_key = _BRUTE_FORCE_BLOCK_KEY.format(ip=client_ip)
    count_key = _BRUTE_FORCE_COUNT_KEY.format(ip=client_ip)

    try:
        # 1. Verificar se há bloqueio progressivo ativo para este IP
        if await redis.exists(block_key):
            ttl = await redis.get_ttl(block_key)
            retry_after = max(ttl, 1)  # Garantir pelo menos 1 segundo

            logger.warning(
                "Requisição bloqueada por brute force",
                extra={
                    "client_ip": client_ip,
                    "endpoint": str(request.url.path),
                    "block_type": "brute_force",
                    "retry_after": retry_after,
                },
            )
            raise HTTPException(
                status_code=429,
                detail="Bloqueado por padrão abusivo detectado.",
                headers={"Retry-After": str(retry_after)},
            )

        # 2. Incrementar contador de violações na janela expandida.
        # Este contador acumula violações de rate limit ao longo do tempo.
        # A lógica de incremento quando há violação de rate limit é feita
        # pelo rate_limit_by_ip; aqui verificamos se o threshold foi atingido.
        threshold = settings.rate_limit_requests * settings.brute_force_threshold_multiplier
        violation_count = await redis.increment_with_ttl(
            count_key,
            ttl_seconds=settings.brute_force_detection_window_seconds,
        )

        if violation_count >= threshold:
            # Ativar bloqueio progressivo
            await redis.set(
                block_key,
                value="1",
                ttl_seconds=settings.brute_force_block_seconds,
            )

            logger.warning(
                "Padrão abusivo detectado — bloqueio progressivo ativado",
                extra={
                    "client_ip": client_ip,
                    "endpoint": str(request.url.path),
                    "block_type": "brute_force",
                    "violation_count": violation_count,
                    "threshold": threshold,
                    "block_seconds": settings.brute_force_block_seconds,
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        # Fail-open: se Redis estiver indisponível, permite a requisição
        logger.warning(
            "Redis indisponível no brute force protection — fail open",
            extra={"client_ip": client_ip, "error": str(e)},
        )
