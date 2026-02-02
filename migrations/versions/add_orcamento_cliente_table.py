"""Add OrcamentoCliente table

Revision ID: add_orcamento_cliente_table
Revises: add_tipo_gasto_to_compra
Create Date: 2025-01-18 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_orcamento_cliente_table'
down_revision = 'add_tipo_gasto_to_compra'
branch_labels = None
depends_on = None


def _inspect_orcamento_cliente():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = "orcamento_cliente"
    if table_name not in inspector.get_table_names():
        return None
    return {
        "columns": {col["name"] for col in inspector.get_columns(table_name)},
        "indexes": {idx["name"] for idx in inspector.get_indexes(table_name)},
        "uniques": {uq["name"] for uq in inspector.get_unique_constraints(table_name)},
    }


def upgrade():
    """Create orcamento_cliente table (idempotent)."""
    state = _inspect_orcamento_cliente()
    if not state:
        op.create_table(
            "orcamento_cliente",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cliente_id", sa.Integer(), nullable=False),
            sa.Column("ano", sa.Integer(), nullable=False),
            sa.Column("mes", sa.Integer(), nullable=True),
            sa.Column(
                "valor_orcamento_custeio",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
                server_default="0.00",
            ),
            sa.Column(
                "valor_orcamento_capital",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
                server_default="0.00",
            ),
            sa.Column(
                "valor_gasto_custeio",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
                server_default="0.00",
            ),
            sa.Column(
                "valor_gasto_capital",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
                server_default="0.00",
            ),
            sa.Column(
                "percentual_alerta_custeio",
                sa.Integer(),
                nullable=False,
                server_default="80",
            ),
            sa.Column(
                "percentual_alerta_capital",
                sa.Integer(),
                nullable=False,
                server_default="80",
            ),
            sa.Column(
                "alerta_ativo_custeio",
                sa.Boolean(),
                nullable=False,
                server_default="true",
            ),
            sa.Column(
                "alerta_ativo_capital",
                sa.Boolean(),
                nullable=False,
                server_default="true",
            ),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["cliente_id"], ["cliente.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "cliente_id", "ano", "mes", name="uq_orcamento_cliente_periodo"
            ),
        )
        state = _inspect_orcamento_cliente()

    columns = state["columns"]
    indexes = state["indexes"]
    uniques = state["uniques"]

    if "cliente_id" in columns and "ix_orcamento_cliente_cliente_id" not in indexes:
        op.create_index(
            "ix_orcamento_cliente_cliente_id",
            "orcamento_cliente",
            ["cliente_id"],
        )
    if (
        "ano" in columns
        and "mes" in columns
        and "ix_orcamento_cliente_ano_mes" not in indexes
    ):
        op.create_index(
            "ix_orcamento_cliente_ano_mes",
            "orcamento_cliente",
            ["ano", "mes"],
        )
    if (
        "cliente_id" in columns
        and "ano" in columns
        and "mes" in columns
        and "uq_orcamento_cliente_periodo" not in uniques
    ):
        op.create_unique_constraint(
            "uq_orcamento_cliente_periodo",
            "orcamento_cliente",
            ["cliente_id", "ano", "mes"],
        )


def downgrade():
    """Drop orcamento_cliente table."""
    state = _inspect_orcamento_cliente()
    if not state:
        return
    indexes = state["indexes"]
    if "ix_orcamento_cliente_ano_mes" in indexes:
        op.drop_index(
            "ix_orcamento_cliente_ano_mes", table_name="orcamento_cliente"
        )
    if "ix_orcamento_cliente_cliente_id" in indexes:
        op.drop_index(
            "ix_orcamento_cliente_cliente_id", table_name="orcamento_cliente"
        )
    op.drop_table("orcamento_cliente")
