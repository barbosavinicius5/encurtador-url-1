"""Adicionar tabela projects.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria a tabela projects."""
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_projects_account_id", "projects", ["account_id"])
    op.create_unique_constraint("uq_projects_name_account", "projects", ["name", "account_id"])


def downgrade() -> None:
    """Remove a tabela projects."""
    op.drop_constraint("uq_projects_name_account", "projects", type_="unique")
    op.drop_index("ix_projects_account_id", table_name="projects")
    op.drop_table("projects")
