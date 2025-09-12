"""merge heads 35467fad63e8 + 38ddeb14ceba

Revision ID: 2a52d4965854
Revises: 35467fad63e8, 38ddeb14ceba
Create Date: 2025-09-12 19:03:31.948849

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a52d4965854'
down_revision = ('35467fad63e8', '38ddeb14ceba')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
