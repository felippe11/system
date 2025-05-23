"""percentual taxa inscricao

Revision ID: b3b7d1f9bcb2
Revises: 2744d4add4b2
Create Date: 2025-04-23 03:21:01.980998

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3b7d1f9bcb2'
down_revision = '2744d4add4b2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('configuracao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('taxa_percentual_inscricao', sa.Numeric(precision=5, scale=2), nullable=True))
        batch_op.drop_column('taxa_fixa_inscricao')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('configuracao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('taxa_fixa_inscricao', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True))
        batch_op.drop_column('taxa_percentual_inscricao')

    # ### end Alembic commands ###
