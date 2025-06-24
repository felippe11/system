"""add review timing fields"""

Revision ID: abcd1234
Revises: edec4bcb5f46
Create Date: 2025-06-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'abcd1234'
down_revision = 'edec4bcb5f46'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('review') as batch_op:
        batch_op.add_column(sa.Column('started_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('finished_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('duration_seconds', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('review') as batch_op:
        batch_op.drop_column('duration_seconds')
        batch_op.drop_column('finished_at')
        batch_op.drop_column('started_at')
