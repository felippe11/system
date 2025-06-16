"""Merge definitivo dos heads

Revision ID: 64d145b137c7
Revises: 17ea7e0df270, 885a38754a79, d7cf3659e660
Create Date: 2025-06-16 14:17:16.571292

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '64d145b137c7'
down_revision = ('17ea7e0df270', '885a38754a79', 'd7cf3659e660')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
