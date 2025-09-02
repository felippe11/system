"""add preco_unitario to material

Revision ID: f275f62d3591
Revises: 970d0a401265
Create Date: 2025-09-02 16:01:02.404373

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f275f62d3591'
down_revision = '085998713db1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('material') as batch_op:
        batch_op.add_column(sa.Column('preco_unitario', sa.Numeric(12, 2), nullable=True))
    op.execute("UPDATE material SET preco_unitario = 0 WHERE preco_unitario IS NULL;")
    with op.batch_alter_table('material') as batch_op:
        batch_op.alter_column('preco_unitario', nullable=False, server_default='0')


def downgrade():
    pass
