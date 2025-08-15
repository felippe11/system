"""create revisor_process_evento_association table

Revision ID: aa9e8e464c3b
Revises: 15b6b890ce1d
Create Date: 2025-02-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "aa9e8e464c3b"
down_revision = "15b6b890ce1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revisor_process_evento_association",
        sa.Column("process_id", sa.Integer, sa.ForeignKey("revisor_process.id"), primary_key=True),
        sa.Column("evento_id", sa.Integer, sa.ForeignKey("evento.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("revisor_process_evento_association")
