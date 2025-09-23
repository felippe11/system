"""merge heads 5b9348f021f4 + df333753e4c7

Revision ID: 35467fad63e8
Revises: 5b9348f021f4, df333753e4c7
Create Date: 2025-09-12 16:58:15.464183

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '35467fad63e8'
down_revision = ('5b9348f021f4', 'df333753e4c7')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
