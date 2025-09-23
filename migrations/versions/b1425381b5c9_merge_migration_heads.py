"""Merge migration heads

Revision ID: b1425381b5c9
Revises: 750863e7b1d2, fix_material_disponivel_columns
Create Date: 2025-09-14 11:20:36.219184

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1425381b5c9'
down_revision = ('750863e7b1d2', 'fix_material_disponivel_columns')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
