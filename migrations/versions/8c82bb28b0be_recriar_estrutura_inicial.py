"""Recriar estrutura inicial

Revision ID: 8c82bb28b0be
Revises: 502e623d3a96
Create Date: 2025-02-23 12:15:01.472114

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c82bb28b0be'
down_revision = '502e623d3a96'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar cliente_id em inscricao
    with op.batch_alter_table('inscricao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cliente_id', sa.Integer(), nullable=True))
    op.execute("UPDATE inscricao SET cliente_id = 1 WHERE cliente_id IS NULL")
    with op.batch_alter_table('inscricao', schema=None) as batch_op:
        batch_op.alter_column('cliente_id', nullable=False)
        batch_op.create_foreign_key(None, 'clientes', ['cliente_id'], ['id'])

    # Adicionar cliente_id em oficina
    with op.batch_alter_table('oficina', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cliente_id', sa.Integer(), nullable=True))
    op.execute("UPDATE oficina SET cliente_id = 1 WHERE cliente_id IS NULL")
    with op.batch_alter_table('oficina', schema=None) as batch_op:
        batch_op.alter_column('cliente_id', nullable=False)
        batch_op.create_foreign_key(None, 'clientes', ['cliente_id'], ['id'])

    # Ajustar cliente_id em usuario (já existe, mas permitir NULL e adicionar FK)
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.alter_column('cliente_id', nullable=True, existing_type=sa.Integer())
        batch_op.create_foreign_key(None, 'clientes', ['cliente_id'], ['id'])

def downgrade():
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        # Não removemos a coluna cliente_id aqui, pois ela já existia antes

    with op.batch_alter_table('oficina', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('cliente_id')

    with op.batch_alter_table('inscricao', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('cliente_id')

    # ### end Alembic commands ###
