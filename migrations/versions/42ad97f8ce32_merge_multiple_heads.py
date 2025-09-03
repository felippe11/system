"""Merge multiple heads

Revision ID: 42ad97f8ce32
Revises: a3fcf490cba3, ba5d2f32e6ec
Create Date: 2025-09-03 17:51:21.211912

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '42ad97f8ce32'
down_revision = ('a3fcf490cba3', 'ba5d2f32e6ec')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
