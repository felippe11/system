"""merge period-related migrations for formularios

Revision ID: 40d6f21cfd81
Revises: f3d9f9a5e8d2
Create Date: 2025-01-01 00:00:00.000000

This migration consolidates the history of period fields on the
``formularios`` table.  No schema changes are performed.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "40d6f21cfd81"
down_revision = "f3d9f9a5e8d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

