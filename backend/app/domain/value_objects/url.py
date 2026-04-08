"""Value Object para validação de URL."""

import re
from dataclasses import dataclass

# Conjunto de caracteres válidos em path, query e fragmento conforme RFC 3986.
# Inclui: unreserved chars, percent-encoding (%XX), sub-delimiters e pchar.
_VALID_URL_CHARS = r"a-zA-Z0-9\-._~%!$&'()*+,;=:@/?"

# Padrão de validação de URL — aceita apenas esquemas http e https (bloqueia
# javascript:, data:, vbscript: e outros esquemas perigosos).
# Suporta: percent-encoding (%20, %2F…), query strings complexas (+, &, =),
# fragmentos (#section), portas, IPs e localhost.
URL_PATTERN = re.compile(
    r"^https?://"  # esquema obrigatório: somente http ou https
    r"(?:"
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?"  # hostname (ex: exemplo.com.br)
    r"|localhost"  # localhost
    r"|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"  # IPv4 (ex: 192.168.1.1)
    r")"
    r"(?::\d+)?"  # porta opcional (ex: :8080)
    r"(?:/[" + _VALID_URL_CHARS + r"]*)?"  # path opcional com chars RFC 3986
    r"(?:\?[" + _VALID_URL_CHARS + r"]*)?"  # query string opcional
    r"(?:#[" + _VALID_URL_CHARS + r"]*)?$",  # fragmento opcional
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UrlValue:
    """Value Object imutável para validação de URL.

    Aceita apenas URLs com esquemas http e https.
    Suporta percent-encoding, query strings complexas e fragmentos (#).
    Rejeita esquemas perigosos: javascript:, data:, vbscript:, ftp: etc.
    """

    value: str

    def __post_init__(self):
        stripped = self.value.strip() if self.value else ""
        if not stripped or not URL_PATTERN.match(stripped):
            raise ValueError(f"URL inválida: '{self.value}'")
