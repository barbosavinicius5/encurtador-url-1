"""Adicionar índices para otimização de queries de projetos (listagem e ordenação).

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-07 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria índices compostos para otimizar listagem de projetos com ordenação."""
    # Índice composto para queries de listagem com ordenação por created_at DESC (CA-04)
    op.create_index(
        "ix_projects_account_id_created_at",
        "projects",
        ["account_id", "created_at"],
    )
    # Índice composto para ordenação por nome
    op.create_index(
        "ix_projects_account_id_name",
        "projects",
        ["account_id", "name"],
    )


def downgrade() -> None:
    """Remove índices compostos de projetos."""
    op.drop_index("ix_projects_account_id_name", table_name="projects")
    op.drop_index("ix_projects_account_id_created_at", table_name="projects")
