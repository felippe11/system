"""merge heads 266851bf54b9 & 1e6c5277571b

Revision ID: 77195f743268
Revises: 266851bf54b9, 1e6c5277571b
Create Date: 2025-08-26 16:02:50.378562

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '77195f743268'
down_revision = ('266851bf54b9', '1e6c5277571b')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
