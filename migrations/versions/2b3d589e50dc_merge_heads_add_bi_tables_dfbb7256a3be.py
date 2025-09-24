"""merge heads add_bi_tables + dfbb7256a3be

Revision ID: 2b3d589e50dc
Revises: add_bi_tables, dfbb7256a3be
Create Date: 2025-09-24 01:56:42.302266

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b3d589e50dc'
down_revision = ('add_bi_tables', 'dfbb7256a3be')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
