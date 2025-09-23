"""Add auto distribution log table

Revision ID: add_auto_distribution_log_table
Revises: fix_assignment_foreign_keys
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_auto_distribution_log_table"
down_revision = "fix_assignment_foreign_keys"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auto_distribution_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("evento_id", sa.Integer, nullable=False),
        sa.Column("total_submissions", sa.Integer, nullable=False),
        sa.Column("total_assignments", sa.Integer, nullable=False),
        sa.Column("distribution_seed", sa.String(length=50), nullable=True),
        sa.Column("conflicts_detected", sa.Integer, nullable=True),
        sa.Column("fallback_assignments", sa.Integer, nullable=True),
        sa.Column("failed_assignments", sa.Integer, nullable=True),
        sa.Column("distribution_details", sa.JSON, nullable=True),
        sa.Column("error_log", sa.JSON, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.ForeignKeyConstraint([
            "evento_id"
        ], ["evento.id"], name="fk_auto_distribution_log_evento", ondelete="CASCADE"),
    )
    op.create_index(
        "idx_auto_distribution_log_evento",
        "auto_distribution_log",
        ["evento_id"],
    )
    op.create_index(
        "idx_auto_distribution_log_started_at",
        "auto_distribution_log",
        ["started_at"],
    )


def downgrade():
    op.drop_index("idx_auto_distribution_log_started_at", table_name="auto_distribution_log")
    op.drop_index("idx_auto_distribution_log_evento", table_name="auto_distribution_log")
    op.drop_table("auto_distribution_log")
