"""Add cliente_id and used to monitor_cadastro_link

Revision ID: 5b9348f021f4
Revises: 32bf7215c932
Create Date: 2025-09-08 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5b9348f021f4"
down_revision = "32bf7215c932"
branch_labels = None
depends_on = None


def upgrade():
    """Add cliente_id and used columns and adjust token length."""
    op.add_column(
        "monitor_cadastro_link",
        sa.Column("cliente_id", sa.Integer(), nullable=False),
    )
    op.add_column(
        "monitor_cadastro_link",
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column(
        "monitor_cadastro_link",
        "token",
        existing_type=sa.String(length=255),
        type_=sa.String(length=36),
        existing_nullable=False,
    )
    op.create_foreign_key(
        "fk_monitor_cadastro_link_cliente_id_cliente",
        "monitor_cadastro_link",
        "cliente",
        ["cliente_id"],
        ["id"],
    )


def downgrade():
    """Revert cliente_id and used columns and token length."""
    op.drop_constraint(
        "fk_monitor_cadastro_link_cliente_id_cliente",
        "monitor_cadastro_link",
        type_="foreignkey",
    )
    op.alter_column(
        "monitor_cadastro_link",
        "token",
        existing_type=sa.String(length=36),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.drop_column("monitor_cadastro_link", "used")
    op.drop_column("monitor_cadastro_link", "cliente_id")
