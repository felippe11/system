"""Merge heads 27f85c2ac4a0 + add_aprovacao_tables + add_orcamento_cliente_table

Revision ID: c439cf81f64a
Revises: 27f85c2ac4a0, add_aprovacao_tables, add_orcamento_cliente_table
Create Date: 2025-09-17 19:34:43.633886

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c439cf81f64a'
down_revision = ('27f85c2ac4a0', 'add_aprovacao_tables', 'add_orcamento_cliente_table')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
