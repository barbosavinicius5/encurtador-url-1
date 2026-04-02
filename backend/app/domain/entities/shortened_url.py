"""Entidade de domínio ShortenedUrl."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ShortenedUrl:
    """Entidade que representa um link encurtado."""

    original_url: str
    short_code: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: int | None = None
