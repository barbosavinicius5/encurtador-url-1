"""Exceptions de domínio tipadas para o encurtador de URLs."""


class DomainError(Exception):
    """Classe base abstrata para todas as exceptions de domínio."""


class InvalidUrlError(DomainError, ValueError):
    """Lançada quando uma URL é inválida ou não está em conformidade com RFC 3986.

    Herda de ValueError para compatibilidade retroativa com código que captura ValueError.
    """

    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"URL inválida '{url}': {reason}")


class MaliciousDomainError(DomainError):
    """Lançada quando uma URL aponta para domínio classificado como phishing/malware."""

    def __init__(self, domain: str):
        self.domain = domain
        super().__init__(f"Domínio bloqueado: {domain}")


class SlugCollisionError(DomainError):
    """Lançada quando o slug gerado já existe no repositório."""

    def __init__(self, slug: str):
        self.slug = slug
        super().__init__(f"Slug já em uso: {slug}")
