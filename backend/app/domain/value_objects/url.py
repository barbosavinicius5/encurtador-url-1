"""Value Object para validação de URL."""

import re
from dataclasses import dataclass

URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UrlValue:
    """Value Object imutável para validação de URL."""

    value: str

    def __post_init__(self):
        if not self.value or not URL_PATTERN.match(self.value):
            raise ValueError(f"URL inválida: '{self.value}'")
