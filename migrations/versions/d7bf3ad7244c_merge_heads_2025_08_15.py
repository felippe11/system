"""merge heads 2025-08-15

Revision ID: d7bf3ad7244c
Revises: 31e6ad1c6a4f, 40d6f21cfd81, 7e82bd7f1e2a, 8b761cbdc50d, 9bac7f9f0073, aa9e8e464c3b, bd69158236c4, c1e36c66e0d4, d9126a645f16
Create Date: 2025-08-15 19:51:37.986521

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7bf3ad7244c'
down_revision = ('31e6ad1c6a4f', '40d6f21cfd81', '7e82bd7f1e2a', '8b761cbdc50d', '9bac7f9f0073', 'aa9e8e464c3b', 'bd69158236c4', 'c1e36c66e0d4', 'd9126a645f16')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
