"""add ordem_exibicao to oficinadia

Revision ID: 1b2c3d4e5f6a
Revises: 0aedd9fbed41
Create Date: 2026-01-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "1b2c3d4e5f6a"
down_revision = "0aedd9fbed41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("oficinadia") as batch_op:
        batch_op.add_column(sa.Column("ordem_exibicao", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("oficinadia") as batch_op:
        batch_op.drop_column("ordem_exibicao")
