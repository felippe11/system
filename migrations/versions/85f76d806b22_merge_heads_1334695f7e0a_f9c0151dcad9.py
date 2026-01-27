"""merge heads 1334695f7e0a + f9c0151dcad9

Revision ID: 85f76d806b22
Revises: 1334695f7e0a, f9c0151dcad9
Create Date: 2025-09-30 12:11:48.973350

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '85f76d806b22'
down_revision = ('1334695f7e0a', 'f9c0151dcad9')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
