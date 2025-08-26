"""empty message

Revision ID: 1502f58fd119
Revises: d1b3a515bc9e
Create Date: 2025-08-25 14:30:55.790036
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1502f58fd119"
down_revision = "d1b3a515bc9e"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("agendamento_visita")]

    if "precisa_transporte" in cols:
        op.drop_column("agendamento_visita", "precisa_transporte")


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("agendamento_visita")]

    if "precisa_transporte" not in cols:
        op.add_column(
            "agendamento_visita",
            sa.Column("precisa_transporte", sa.Boolean(), nullable=True),
        )
