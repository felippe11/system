"""Add estado column to agendamento_visita

Revision ID: 32bf7215c932
Revises: ccf553bc9e47
Create Date: 2025-09-08 16:19:30.983084

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '32bf7215c932'
down_revision = 'ccf553bc9e47'
branch_labels = None
depends_on = None


def upgrade():
    """Add the estado column to agendamento_visita."""
    with op.batch_alter_table("agendamento_visita", schema=None) as batch_op:
        batch_op.add_column(sa.Column("estado", sa.String(length=2), nullable=True))


def downgrade():
    """Remove the estado column from agendamento_visita."""
    with op.batch_alter_table("agendamento_visita", schema=None) as batch_op:
        batch_op.drop_column("estado")
