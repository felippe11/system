"""nova feature

Revision ID: 7d9bf72dc081
Revises: abc123456789
Create Date: 2025-07-01 12:06:42.126786

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "7d9bf72dc081"
down_revision = "abc123456789"
branch_labels = None
depends_on = None


def _has_column(connection, table_name: str, column_name: str) -> bool:
    """Return True if the given column exists in the table."""
    inspector = Inspector.from_engine(connection)
    return column_name in [col["name"] for col in inspector.get_columns(table_name)]


def upgrade() -> None:
    """Add new columns to revisor_process, only if they don't already exist."""
    bind = op.get_bind()

    with op.batch_alter_table("revisor_process") as batch_op:
        if not _has_column(bind, "revisor_process", "availability_start"):
            batch_op.add_column(sa.Column("availability_start", sa.DateTime(), nullable=True))

        if not _has_column(bind, "revisor_process", "availability_end"):
            batch_op.add_column(sa.Column("availability_end", sa.DateTime(), nullable=True))

        if not _has_column(bind, "revisor_process", "exibir_para_participantes"):
            batch_op.add_column(sa.Column("exibir_para_participantes", sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Drop the columns if they exist (reverse of upgrade)."""
    bind = op.get_bind()

    with op.batch_alter_table("revisor_process") as batch_op:
        if _has_column(bind, "revisor_process", "exibir_para_participantes"):
            batch_op.drop_column("exibir_para_participantes")

        if _has_column(bind, "revisor_process", "availability_end"):
            batch_op.drop_column("availability_end")

        if _has_column(bind, "revisor_process", "availability_start"):
            batch_op.drop_column("availability_start")
