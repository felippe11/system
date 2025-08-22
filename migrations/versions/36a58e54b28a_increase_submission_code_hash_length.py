"""increase submission code_hash length

Revision ID: 36a58e54b28a
Revises: 79c3c0f95577
Create Date: 2025-08-21 23:51:10.209505

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '36a58e54b28a'
down_revision = '79c3c0f95577'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'submission',
        'code_hash',
        existing_type=sa.String(length=128),
        type_=sa.String(length=256),
    )


def downgrade():
    op.alter_column(
        'submission',
        'code_hash',
        existing_type=sa.String(length=256),
        type_=sa.String(length=128),
    )
