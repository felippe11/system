"""add tipos_inscricao_permitidos to oficina

Revision ID: 2c3d4e5f6a7b
Revises: 1b2c3d4e5f6a
Create Date: 2026-01-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "2c3d4e5f6a7b"
down_revision = "1b2c3d4e5f6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("oficina") as batch_op:
        batch_op.add_column(sa.Column("tipos_inscricao_permitidos", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("oficina") as batch_op:
        batch_op.drop_column("tipos_inscricao_permitidos")
