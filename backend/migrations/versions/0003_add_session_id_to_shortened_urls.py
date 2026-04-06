"""Adicionar session_id à tabela shortened_urls.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona coluna session_id e índice à tabela shortened_urls."""
    op.add_column(
        "shortened_urls",
        sa.Column("session_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_shortened_urls_session_id",
        "shortened_urls",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove a coluna session_id e o índice da tabela shortened_urls."""
    op.drop_index("ix_shortened_urls_session_id", table_name="shortened_urls")
    op.drop_column("shortened_urls", "session_id")
