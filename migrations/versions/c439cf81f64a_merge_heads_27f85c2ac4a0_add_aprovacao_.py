"""Merge heads add_orcamento_cliente_table + add_aprovacao_tables

Revision ID: c439cf81f64a
Revises: add_orcamento_cliente_table, add_aprovacao_tables
Create Date: 2025-09-17 19:34:43.633886
"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision = "c439cf81f64a"
down_revision = ("add_orcamento_cliente_table", "add_aprovacao_tables")
branch_labels = None
depends_on = None


def upgrade():
    # Merge-only revision: nenhuma alteração de schema necessária.
    pass


def downgrade():
    # Reverte apenas o merge.
    pass
