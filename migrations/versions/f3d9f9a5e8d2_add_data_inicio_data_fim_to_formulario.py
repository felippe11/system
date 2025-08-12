"""historic placeholder for period fields on ``formularios``

Revision ID: f3d9f9a5e8d2
Revises: a4e781302f2b
Create Date: 2024-08-11 20:38:00.000000

This revision originally attempted to add the ``data_inicio`` and
``data_fim`` columns to the ``formularios`` table.  Those columns were
introduced earlier in ``a4e781302f2b``.  The operations were removed to
avoid duplicate column errors, leaving this migration as a no-op that
preserves the historical record.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f3d9f9a5e8d2"
down_revision = "a4e781302f2b"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
