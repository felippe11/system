"""add table for review email failures"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6d0c1bfa2e5b"
down_revision = "25eb3573df18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_email_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("review.id"), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("review_email_log")
