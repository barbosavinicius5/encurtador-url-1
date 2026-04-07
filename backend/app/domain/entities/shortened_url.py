"""Entidade de domínio ShortenedUrl."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional


@dataclass
class ShortenedUrl:
    """Entidade que representa um link encurtado.

    Expõe métodos de comportamento para encapsular a lógica de domínio,
    evitando o antipadrão de entidade anêmica.
    """

    original_url: str
    short_code: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: int | None = None
    click_count: int = 0
    deleted_at: Optional[datetime] = None
    session_id: Optional[str] = None
    last_clicked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def register_click(self, timestamp: Optional[datetime] = None) -> None:
        """Registra um acesso ao link encurtado.

        Incrementa o contador de cliques e atualiza o timestamp do último acesso.

        Args:
            timestamp: Momento do clique. Se None, usa datetime.now(UTC).
        """
        self.click_count += 1
        self.last_clicked_at = timestamp or datetime.now(UTC)

    def is_expired(self) -> bool:
        """Verifica se o link expirou com base no TTL configurado.

        Returns:
            True se expires_at está definido e já passou, False caso contrário.
        """
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at
