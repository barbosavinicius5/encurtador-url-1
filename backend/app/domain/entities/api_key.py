"""Entidade de domínio ApiKey."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional


@dataclass
class ApiKey:
    """Entidade que representa uma chave de acesso à API."""

    key: str
    owner: str
    id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
