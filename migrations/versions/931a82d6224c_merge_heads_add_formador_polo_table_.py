"""Merge heads add_formador_polo_table + b1425381b5c9 + bbe3b046c06e

Revision ID: 931a82d6224c
Revises: add_formador_polo_table, b1425381b5c9, bbe3b046c06e
Create Date: 2025-09-16 12:41:07.139625

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '931a82d6224c'
down_revision = ('add_formador_polo_table', 'b1425381b5c9', 'bbe3b046c06e')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
