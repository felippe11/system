"""Add usage_count column and drop used from monitor_cadastro_link"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c9a2d4f2b6d1"
down_revision = "5b9348f021f4"
branch_labels = None
depends_on = None


def _insp():
    return sa.inspect(op.get_bind())


def _get_columns(table_name: str) -> dict[str, dict]:
    insp = _insp()
    columns: dict[str, dict] = {}
    for column in insp.get_columns(table_name):
        columns[column["name"]] = column
    return columns


def upgrade():
    table = "monitor_cadastro_link"
    columns = _get_columns(table)

    if "usage_count" not in columns:
        op.add_column(
            table,
            sa.Column(
                "usage_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
        op.execute(sa.text(f"UPDATE {table} SET usage_count = 0 WHERE usage_count IS NULL"))
        op.alter_column(table, "usage_count", server_default=None)

    columns = _get_columns(table)
    if "used" in columns:
        op.drop_column(table, "used")


def downgrade():
    table = "monitor_cadastro_link"
    columns = _get_columns(table)

    if "used" not in columns:
        op.add_column(
            table,
            sa.Column(
                "used",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
        # Recalcula estado de uso com base na contagem
        op.execute(
            sa.text(
                f"UPDATE {table} SET used = 1 WHERE usage_count IS NOT NULL AND usage_count > 0"
            )
        )
        op.alter_column(table, "used", server_default=None)

    columns = _get_columns(table)
    if "usage_count" in columns:
        op.drop_column(table, "usage_count")
