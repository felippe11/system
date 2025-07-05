"""merge heads: tipos_inscricao + submission_only + evento_formulario

Revision ID: 62155860b670
Revises: 3c3a378fdd, c1a2b3d4e5f6, d33e6d59d2e3
Create Date: 2025-07-05 02:06:30.631818

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '62155860b670'
down_revision = ('3c3a378fdd', 'c1a2b3d4e5f6', 'd33e6d59d2e3')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
