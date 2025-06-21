"""add taxa_diferenciada column to ConfiguracaoCliente

Revision ID: edec4bcb5f46
Revises: 5883528bda20
Create Date: 2025-08-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'edec4bcb5f46'
down_revision = '5883528bda20'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('configuracao_cliente') as batch_op:
        batch_op.add_column(sa.Column('taxa_diferenciada', sa.Numeric(5, 2), nullable=True))


def downgrade():
    with op.batch_alter_table('configuracao_cliente') as batch_op:
        batch_op.drop_column('taxa_diferenciada')
