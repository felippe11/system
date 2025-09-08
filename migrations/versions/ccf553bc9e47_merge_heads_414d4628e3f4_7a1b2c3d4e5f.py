"""Merge heads 414d4628e3f4 + 7a1b2c3d4e5f

Revision ID: ccf553bc9e47
Revises: 414d4628e3f4, 7a1b2c3d4e5f
Create Date: 2025-09-08 16:11:19.012153

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ccf553bc9e47'
down_revision = ('414d4628e3f4', '7a1b2c3d4e5f')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
