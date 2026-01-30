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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    """Add the estado column to agendamento_visita."""
    with op.batch_alter_table("agendamento_visita", schema=None) as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns("agendamento_visita")}
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("agendamento_visita")}
        if "estado" not in existing_cols:
            batch_op.add_column(sa.Column("estado", sa.String(length=2), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    """Remove the estado column from agendamento_visita."""
    with op.batch_alter_table("agendamento_visita", schema=None) as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns("agendamento_visita")}
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("agendamento_visita")}
        batch_op.drop_column("estado")
