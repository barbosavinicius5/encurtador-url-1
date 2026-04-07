"""Validador extensível de domínios maliciosos."""

import logging
from urllib.parse import urlparse

from app.domain.exceptions import MaliciousDomainError

logger = logging.getLogger(__name__)


class MaliciousDomainValidator:
    """Validador que rejeita URLs com domínios de phishing ou malware.

    Implementa o protocolo UrlValidator: validate(url: str) -> None.
    """

    def __init__(self, blocked_domains: list[str]):
        """Inicializa o validador com a lista de domínios bloqueados.

        Args:
            blocked_domains: Lista de domínios a serem bloqueados (case-insensitive).
        """
        self._blocked = [d.strip().lower() for d in blocked_domains if d.strip()]

    def validate(self, url: str) -> None:
        """Valida que a URL não aponta para domínio malicioso.

        Args:
            url: A URL a ser validada.

        Raises:
            MaliciousDomainError: Se o domínio estiver na lista de bloqueio.
        """
        domain = (urlparse(url).hostname or "").lower()
        for blocked in self._blocked:
            if domain == blocked or domain.endswith(f".{blocked}"):
                logger.warning(
                    "URL rejeitada por domínio malicioso",
                    extra={"blocked_domain": blocked},
                )
                raise MaliciousDomainError(domain=domain)
