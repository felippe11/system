"""add estado column to agendamento_visita

Revision ID: 7a1b2c3d4e5f
Revises: f592acec47c1
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "7a1b2c3d4e5f"
down_revision = "f592acec47c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col['name'] for col in inspector.get_columns("agendamento_visita")}
    if "estado" not in existing_cols:
        op.add_column(
            "agendamento_visita",
            sa.Column("estado", sa.String(length=2), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("agendamento_visita", "estado")

