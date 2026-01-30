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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    with op.batch_alter_table('material', schema=None) as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns("material")}
        if "preco_unitario" not in existing_cols:
            batch_op.add_column(sa.Column('preco_unitario', sa.Float(), nullable=True))
        if "data_atualizacao" not in existing_cols:
            batch_op.add_column(
                sa.Column(
                    'data_atualizacao',
                    sa.DateTime(),
                    server_default=sa.func.now(),
                    nullable=True,
                )
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    with op.batch_alter_table('material', schema=None) as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns("material")}
        if "data_atualizacao" in existing_cols:
            batch_op.drop_column('data_atualizacao')
        if "preco_unitario" in existing_cols:
            batch_op.drop_column('preco_unitario')
