"""Merge heads 1c9a4f2b3d7e and 9b4a2f1c7d8e.

Revision ID: 7abd8980fd92
Revises: 1c9a4f2b3d7e, 9b4a2f1c7d8e
Create Date: 2026-01-30 00:00:00
"""

from alembic import op  # noqa: F401


# revision identifiers, used by Alembic.
revision = "7abd8980fd92"
down_revision = ("1c9a4f2b3d7e", "9b4a2f1c7d8e")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
