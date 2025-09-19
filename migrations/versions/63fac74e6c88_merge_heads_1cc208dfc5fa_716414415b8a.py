"""Merge heads 1cc208dfc5fa + 716414415b8a

Revision ID: 63fac74e6c88
Revises: 1cc208dfc5fa, 716414415b8a
Create Date: 2025-09-19 12:04:25.274080

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '63fac74e6c88'
down_revision = ('1cc208dfc5fa', '716414415b8a')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
