"""Merge multiple heads

Revision ID: 0daa64767343
Revises: 77195f743268, e10db5af1c00
Create Date: 2025-08-27 13:02:15.944379

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0daa64767343'
down_revision = ('77195f743268', 'e10db5af1c00')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
