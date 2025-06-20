"""add review settings columns to ConfiguracaoCliente

Revision ID: 7a34e60bbcaf
Revises: 16e80ff4acb5
Create Date: 2025-07-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7a34e60bbcaf'
down_revision = '16e80ff4acb5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('configuracao_cliente') as batch_op:
        batch_op.add_column(sa.Column('review_model', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('num_revisores_min', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('num_revisores_max', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('prazo_parecer_dias', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('configuracao_cliente') as batch_op:
        batch_op.drop_column('prazo_parecer_dias')
        batch_op.drop_column('num_revisores_max')
        batch_op.drop_column('num_revisores_min')
        batch_op.drop_column('review_model')
