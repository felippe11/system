"""Add unique constraint to declaracao_template

Revision ID: 03b7e3c050f6
Revises: 42ad97f8ce32
Create Date: 2025-09-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "03b7e3c050f6"
down_revision = "42ad97f8ce32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_declaracao_template_cliente_nome"),
        "declaracao_template",
        ["cliente_id", "nome"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_declaracao_template_cliente_nome"),
        "declaracao_template",
        type_="unique",
    )
