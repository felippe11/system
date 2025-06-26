"""add required field flags to ConfiguracaoCliente

Revision ID: fe25f1583d6c
Revises: edec4bcb5f46
Create Date: 2025-09-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fe25f1583d6c'
down_revision = 'edec4bcb5f46'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('configuracao_cliente') as batch_op:
        batch_op.add_column(sa.Column('obrigatorio_nome', sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.add_column(sa.Column('obrigatorio_cpf', sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.add_column(sa.Column('obrigatorio_email', sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.add_column(sa.Column('obrigatorio_senha', sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.add_column(sa.Column('obrigatorio_formacao', sa.Boolean(), nullable=True, server_default=sa.true()))


def downgrade():
    with op.batch_alter_table('configuracao_cliente') as batch_op:
        batch_op.drop_column('obrigatorio_formacao')
        batch_op.drop_column('obrigatorio_senha')
        batch_op.drop_column('obrigatorio_email')
        batch_op.drop_column('obrigatorio_cpf')
        batch_op.drop_column('obrigatorio_nome')
