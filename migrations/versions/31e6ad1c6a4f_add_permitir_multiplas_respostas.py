"""Add permitir_multiplas_respostas to formularios

Revision ID: 31e6ad1c6a4f
Revises: 15b6b890ce1d
Create Date: 2024-05-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "31e6ad1c6a4f"
down_revision = "15b6b890ce1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "formularios",
        sa.Column("permitir_multiplas_respostas", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("formularios", "permitir_multiplas_respostas")
