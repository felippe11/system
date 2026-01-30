"""add nome descricao status to revisor_process

Revision ID: a5b321c0b871
Revises: 79c3c0f95577
Create Date: 2024-05-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a5b321c0b871"
down_revision = "79c3c0f95577"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col['name'] for col in inspector.get_columns("revisor_process")}
    if "nome" not in existing_cols:
        op.add_column(
            "revisor_process",
            sa.Column("nome", sa.String(length=255), nullable=False, server_default=""),
        )
    existing_cols = {col['name'] for col in inspector.get_columns("revisor_process")}
    if "descricao" not in existing_cols:
        op.add_column(
            "revisor_process",
            sa.Column("descricao", sa.Text(), nullable=True),
        )
    existing_cols = {col['name'] for col in inspector.get_columns("revisor_process")}
    if "status" not in existing_cols:
        op.add_column(
            "revisor_process",
            sa.Column("status", sa.String(length=50), nullable=False, server_default="ativo"),
        )


def downgrade():
    op.drop_column("revisor_process", "status")
    op.drop_column("revisor_process", "descricao")
    op.drop_column("revisor_process", "nome")
