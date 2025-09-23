"""merge heads 0526210919ba + 3e8944025bb5

Revision ID: 266851bf54b9
Revises: 0526210919ba, 3e8944025bb5
Create Date: 2025-08-26 15:20:49.818465

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '266851bf54b9'
down_revision = ('0526210919ba', '3e8944025bb5')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
