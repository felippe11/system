"""Add tipo_gasto field to Compra model

Revision ID: add_tipo_gasto_to_compra
Revises: 27f85c2ac4a0
Create Date: 2025-01-18 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_tipo_gasto_to_compra"
down_revision = "27f85c2ac4a0"  # MIGRAÇÃO QUE CRIA A TABELA 'compra'
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    insp = sa.inspect(bind)
    return table_name in insp.get_table_names()


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    insp = sa.inspect(bind)
    try:
        cols = [c["name"] for c in insp.get_columns(table_name)]
    except Exception:
        return False
    return column_name in cols


def upgrade():
    """Add tipo_gasto column to compra table."""
    bind = op.get_bind()
    table = "compra"
    col = "tipo_gasto"

    if not _table_exists(bind, table):
        raise RuntimeError(
            "Tabela 'compra' não existe. Esta revisão deve rodar após a criação de 'compra' (27f85c2ac4a0)."
        )

    if not _column_exists(bind, table, col):
        op.add_column(
            table,
            sa.Column(col, sa.String(length=20), nullable=False, server_default="custeio"),
        )
        # remove o default no schema (mantém só no model)
        op.alter_column(table, col, server_default=None)


def downgrade():
    """Remove tipo_gasto column from compra table."""
    bind = op.get_bind()
    table = "compra"
    col = "tipo_gasto"

    if _table_exists(bind, table) and _column_exists(bind, table, col):
        op.drop_column(table, col)
