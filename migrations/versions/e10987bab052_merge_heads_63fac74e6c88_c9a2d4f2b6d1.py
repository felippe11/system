"""merge heads 63fac74e6c88 + c9a2d4f2b6d1

Revision ID: e10987bab052
Revises: 63fac74e6c88, c9a2d4f2b6d1
Create Date: 2025-09-19 15:56:39.009762

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e10987bab052'
down_revision = ('63fac74e6c88', 'c9a2d4f2b6d1')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
