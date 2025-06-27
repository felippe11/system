"""merge heads

Revision ID: 32b5e5b73833
Revises: 2b55b8a15aaf, fe25f1583d6c
Create Date: 2025-06-26 17:14:03.150263

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '32b5e5b73833'
down_revision = ('2b55b8a15aaf', 'fe25f1583d6c')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
