"""empty message

Revision ID: 8de5ceef817a
Revises: 
Create Date: 2025-03-24 11:06:34.488775

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8de5ceef817a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('oficina', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tipo_inscricao', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('tipo_oficina', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('tipo_oficina_outro', sa.String(length=100), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('oficina', schema=None) as batch_op:
        batch_op.drop_column('tipo_oficina_outro')
        batch_op.drop_column('tipo_oficina')
        batch_op.drop_column('tipo_inscricao')

    # ### end Alembic commands ###
