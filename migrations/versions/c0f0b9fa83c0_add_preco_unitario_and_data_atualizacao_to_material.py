"""add unit price and update timestamp to material

Revision ID: c0f0b9fa83c0
Revises: 3e8944025bb5
Create Date: 2025-02-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0f0b9fa83c0'
down_revision = '3e8944025bb5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('material', schema=None) as batch_op:
        batch_op.add_column(sa.Column('preco_unitario', sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column('data_atualizacao', sa.DateTime(), server_default=sa.func.now(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('material', schema=None) as batch_op:
        batch_op.drop_column('data_atualizacao')
        batch_op.drop_column('preco_unitario')

