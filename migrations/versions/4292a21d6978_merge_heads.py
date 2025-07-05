"""merge heads

Revision ID: 4292a21d6978
Revises: 123456789abc, 62155860b670, e4cb3d4630b1
Create Date: 2025-07-05 02:56:14.277789

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4292a21d6978'
down_revision = ('123456789abc', '62155860b670', 'e4cb3d4630b1')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
