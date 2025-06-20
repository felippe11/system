"""Add num_vencedores column to sorteio table

Revision ID: 6cffbe38b1e8
Revises: b3b7d1f9bcb2
Create Date: 2025-05-11 23:47:21.432094

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6cffbe38b1e8'
down_revision = 'b3b7d1f9bcb2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('proposta')
    with op.batch_alter_table('feedback_campo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cliente_id', sa.Integer(), nullable=True))
        batch_op.alter_column('ministrante_id',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.create_foreign_key(
            'fk_feedback_campo_cliente_id_cliente',
            'cliente', ['cliente_id'], ['id']
        )

    with op.batch_alter_table('sorteio', schema=None) as batch_op:
        batch_op.add_column(sa.Column('num_vencedores', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('sorteio', schema=None) as batch_op:
        batch_op.drop_column('num_vencedores')

    with op.batch_alter_table('feedback_campo', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_feedback_campo_cliente_id_cliente',
            type_='foreignkey'
        )
        batch_op.alter_column('ministrante_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.drop_column('cliente_id')

    op.create_table('proposta',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('nome', sa.VARCHAR(length=150), autoincrement=False, nullable=True),
    sa.Column('email', sa.VARCHAR(length=150), autoincrement=False, nullable=False),
    sa.Column('tipo_evento', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('descricao', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('data_submissao', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('status', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='proposta_pkey')
    )
    # ### end Alembic commands ###
