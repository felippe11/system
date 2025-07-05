"""add submissao_aberta to Evento

Revision ID: e4cb3d4630b1
Revises: ffbc68259c84
Create Date: 2025-12-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'e4cb3d4630b1'
down_revision = 'ffbc68259c84'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('evento') as batch_op:
        batch_op.add_column(sa.Column('submissao_aberta', sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('evento') as batch_op:
        batch_op.drop_column('submissao_aberta')
