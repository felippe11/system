"""merge heads 0526210919ba + 3e8944025bb5

Revision ID: 2f01fce91968
Revises: 0526210919ba, 3e8944025bb5
Create Date: 2025-08-26 15:16:49.107564

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f01fce91968'
down_revision = ('0526210919ba', '3e8944025bb5')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
