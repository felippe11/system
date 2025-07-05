"""add tipos_inscricao_permitidos column

Revision ID: 3c3a378fdd
Revises: 7d9bf72dc081
Create Date: 2025-10-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '3c3a378fdd'
down_revision = '7d9bf72dc081'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('configuracao_agendamento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tipos_inscricao_permitidos', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('configuracao_agendamento', schema=None) as batch_op:
        batch_op.drop_column('tipos_inscricao_permitidos')
