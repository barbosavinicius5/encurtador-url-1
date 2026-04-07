"""Value Object para validação de URL com conformidade RFC 3986."""

import logging
from urllib.parse import urlparse

from app.domain.exceptions import InvalidUrlError, MaliciousDomainError
from app.domain.sanitization import sanitize_url

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = ("http", "https")


class UrlValue:
    """Value Object imutável para validação de URL com conformidade RFC 3986.

    Valida:
        - Scheme: apenas http e https são permitidos
        - Host: não pode ser vazio
        - Blocklist: domínios de phishing/malware são rejeitados

    Sanitização é aplicada antes de qualquer validação estrutural.
    """

    __slots__ = ("_url",)

    def __init__(self, url: str, blocked_domains: list[str] | None = None):
        """Inicializa e valida o Value Object URL.

        Args:
            url: A URL a ser validada e encurtada.
            blocked_domains: Lista opcional de domínios bloqueados (phishing/malware).

        Raises:
            InvalidUrlError: Se a URL não estiver em conformidade com RFC 3986
                            ou exceder o tamanho máximo.
            MaliciousDomainError: Se o domínio estiver na lista de bloqueio.
        """
        # Sanitiza antes de qualquer validação
        sanitized = sanitize_url(url)

        # Parse da URL para validação estrutural
        parsed = urlparse(sanitized)

        # Valida scheme (apenas http/https)
        if parsed.scheme not in _ALLOWED_SCHEMES:
            raise InvalidUrlError(
                url=sanitized,
                reason=f"scheme '{parsed.scheme}' não permitido; use http ou https",
            )

        # Valida host não-vazio
        if not parsed.netloc:
            raise InvalidUrlError(
                url=sanitized,
                reason="host ausente",
            )

        # Verifica blocklist de domínios maliciosos
        domain = (parsed.hostname or "").lower()
        for blocked in blocked_domains or []:
            blocked_lower = blocked.strip().lower()
            if domain == blocked_lower or domain.endswith(f".{blocked_lower}"):
                logger.warning(
                    "URL rejeitada por domínio malicioso",
                    extra={"blocked_domain": blocked_lower},
                )
                raise MaliciousDomainError(domain=domain)

        object.__setattr__(self, "_url", sanitized)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("UrlValue é imutável")

    @property
    def value(self) -> str:
        """Retorna o valor da URL sanitizada e validada."""
        return self._url
