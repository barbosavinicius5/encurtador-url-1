"""Criar tabela shortened_urls.

Revision ID: 0001
Revises:
Create Date: 2025-01-31 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria a tabela shortened_urls com índice no short_code."""
    op.create_table(
        "shortened_urls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("original_url", sa.String(), nullable=False),
        sa.Column("short_code", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("short_code"),
    )
    op.create_index(
        op.f("ix_shortened_urls_short_code"), "shortened_urls", ["short_code"], unique=True
    )


def downgrade() -> None:
    """Remove a tabela shortened_urls."""
    op.drop_index(op.f("ix_shortened_urls_short_code"), table_name="shortened_urls")
    op.drop_table("shortened_urls")
