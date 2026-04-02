"""Adicionar click_count e deleted_at à tabela shortened_urls.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona colunas click_count e deleted_at à tabela shortened_urls."""
    op.add_column(
        "shortened_urls",
        sa.Column(
            "click_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "shortened_urls",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove as colunas click_count e deleted_at da tabela shortened_urls."""
    op.drop_column("shortened_urls", "deleted_at")
    op.drop_column("shortened_urls", "click_count")
