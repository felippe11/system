# Add evento_id to submission.

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b460e470d7a9"
down_revision = ("97ff1ac3c1dc", "b1aa30258a43")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "submission",
        sa.Column("evento_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_submission_evento",
        "submission",
        "evento",
        ["evento_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_submission_evento", "submission", type_="foreignkey")
    op.drop_column("submission", "evento_id")
