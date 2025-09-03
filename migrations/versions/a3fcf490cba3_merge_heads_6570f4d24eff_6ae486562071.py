"""merge heads 6570f4d24eff + 6ae486562071

Revision ID: a3fcf490cba3
Revises: 6570f4d24eff, 6ae486562071
Create Date: 2025-09-03 00:23:48.851879

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3fcf490cba3'
down_revision = ('6570f4d24eff', '6ae486562071')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
