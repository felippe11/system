"""merge placeholder linking 32bf7215c932 to b028d7157f10

Revision ID: f2205e8d2be8
Revises: 32bf7215c932
Create Date: 2025-09-09 08:51:59.000000

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision = 'f2205e8d2be8'
down_revision = '32bf7215c932'
branch_labels = None
depends_on = None


def upgrade():
    # This is an empty merge/placeholder revision. No schema changes.
    pass


def downgrade():
    # This placeholder introduces no changes to undo.
    pass

