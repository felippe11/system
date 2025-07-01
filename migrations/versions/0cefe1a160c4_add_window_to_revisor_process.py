"""add availability window to RevisorProcess

Revision ID: 0cefe1a160c4
Revises: f123456789ab
Create Date: 2025-10-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0cefe1a160c4'
down_revision = 'f123456789ab'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('revisor_process') as batch_op:
        batch_op.add_column(sa.Column('data_inicio', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('data_fim', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('revisor_process') as batch_op:
        batch_op.drop_column('data_fim')
        batch_op.drop_column('data_inicio')
