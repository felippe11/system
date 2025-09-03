"""set material ativo not null

Revision ID: e5c80c0b2a3c
Revises: c0f0b9fa83c0
Create Date: 2025-02-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e5c80c0b2a3c'
down_revision = 'c0f0b9fa83c0'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("UPDATE material SET ativo = true WHERE ativo IS NULL")
    with op.batch_alter_table('material', schema=None) as batch_op:
        batch_op.alter_column(
            'ativo',
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        )

def downgrade():
    with op.batch_alter_table('material', schema=None) as batch_op:
        batch_op.alter_column(
            'ativo',
            existing_type=sa.Boolean(),
            nullable=True,
            server_default=None,
        )
