"""Add categoria to atividade_multipla_data

Revision ID: 1c9a4f2b3d7e
Revises: d4889a23ebd8
Create Date: 2026-01-30 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c9a4f2b3d7e'
down_revision = 'd4889a23ebd8'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    with op.batch_alter_table('atividade_multipla_data', schema=None) as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns('atividade_multipla_data')}
        if 'categoria' not in existing_cols:
            batch_op.add_column(sa.Column('categoria', sa.String(length=100), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    with op.batch_alter_table('atividade_multipla_data', schema=None) as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns('atividade_multipla_data')}
        if 'categoria' in existing_cols:
            batch_op.drop_column('categoria')
