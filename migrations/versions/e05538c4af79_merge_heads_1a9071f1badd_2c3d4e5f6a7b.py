"""merge heads 1a9071f1badd 2c3d4e5f6a7b

Revision ID: e05538c4af79
Revises: 1a9071f1badd, 2c3d4e5f6a7b
Create Date: 2026-01-30 00:48:24.000000
"""

from alembic import op

revision = "e05538c4af79"
down_revision = ("1a9071f1badd", "2c3d4e5f6a7b")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only migration, no schema changes.
    pass


def downgrade() -> None:
    # Merge-only migration, no schema changes.
    pass
