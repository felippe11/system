"""add quota columns to ConfiguracaoCliente

Revision ID: a9b024c1d234
Revises: 7715d38d1175
Create Date: 2026-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a9b024c1d234'
down_revision = '7715d38d1175'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('configuracao_cliente') as batch_op:
        batch_op.add_column(sa.Column('limite_eventos', sa.Integer(), nullable=True, server_default='5'))
        batch_op.add_column(sa.Column('limite_inscritos', sa.Integer(), nullable=True, server_default='1000'))
        batch_op.add_column(sa.Column('limite_formularios', sa.Integer(), nullable=True, server_default='3'))
        batch_op.add_column(sa.Column('limite_revisores', sa.Integer(), nullable=True, server_default='2'))


def downgrade():
    with op.batch_alter_table('configuracao_cliente') as batch_op:
        batch_op.drop_column('limite_revisores')
        batch_op.drop_column('limite_formularios')
        batch_op.drop_column('limite_inscritos')
        batch_op.drop_column('limite_eventos')
