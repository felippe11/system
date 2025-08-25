"""merge heads 1502f58fd119 + a74fa7e7d502

Revision ID: 8c3e31c94ace
Revises: 1502f58fd119, a74fa7e7d502
Create Date: 2025-08-25 16:28:19.692372

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c3e31c94ace'
down_revision = ('1502f58fd119', 'a74fa7e7d502')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
