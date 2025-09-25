"""merge heads add_assignment_reevaluation_flag + b367611ada28

Revision ID: 4e433a7fffc8
Revises: add_assignment_reevaluation_flag, b367611ada28
Create Date: 2025-09-25 20:55:25.749763

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4e433a7fffc8'
down_revision = ('add_assignment_reevaluation_flag', 'b367611ada28')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
