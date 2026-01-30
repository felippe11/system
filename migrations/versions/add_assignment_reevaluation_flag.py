"""Add is_reevaluation flag to assignment

Revision ID: add_assignment_reevaluation_flag
Revises: add_assignment_extensions
Create Date: 2025-02-15 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_assignment_reevaluation_flag"
down_revision = "add_assignment_extensions"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col['name'] for col in inspector.get_columns("assignment")}
    if "is_reevaluation" not in existing_cols:
        op.add_column(
            "assignment",
            sa.Column(
                "is_reevaluation",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    # Remove the server default to avoid affecting future inserts implicitly
    op.alter_column(
        "assignment",
        "is_reevaluation",
        server_default=None,
    )


def downgrade():
    op.drop_column("assignment", "is_reevaluation")

