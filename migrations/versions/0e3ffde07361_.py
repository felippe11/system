"""empty message

Revision ID: 0e3ffde07361
Revises: c20b45a05c90
Create Date: 2025-09-19 17:54:26.522796

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0e3ffde07361'
down_revision = 'c20b45a05c90'
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
        "foreign_keys": {fk["name"] for fk in inspector.get_foreign_keys(table_name)},
        "uniques": {uq["name"] for uq in inspector.get_unique_constraints(table_name)},
    }


def upgrade():
    state = _inspect_orcamento_cliente()
    if not state:
        return

    columns = state["columns"]
    indexes = state["indexes"]
    foreign_keys = state["foreign_keys"]
    uniques = state["uniques"]

    should_create_fk = "fk_orcamento_cliente_cliente_id_cliente" not in foreign_keys

    with op.batch_alter_table("orcamento_cliente", schema=None) as batch_op:
        if "valor_total_disponivel" not in columns:
            batch_op.add_column(
                sa.Column("valor_total_disponivel", sa.Float(), nullable=False)
            )
        if "valor_custeio_disponivel" not in columns:
            batch_op.add_column(
                sa.Column("valor_custeio_disponivel", sa.Float(), nullable=False)
            )
        if "valor_capital_disponivel" not in columns:
            batch_op.add_column(
                sa.Column("valor_capital_disponivel", sa.Float(), nullable=False)
            )
        if "valor_alerta_total" not in columns:
            batch_op.add_column(
                sa.Column("valor_alerta_total", sa.Float(), nullable=False)
            )
        if "valor_alerta_custeio" not in columns:
            batch_op.add_column(
                sa.Column("valor_alerta_custeio", sa.Float(), nullable=False)
            )
        if "valor_alerta_capital" not in columns:
            batch_op.add_column(
                sa.Column("valor_alerta_capital", sa.Float(), nullable=False)
            )
        if "ano_orcamento" not in columns:
            batch_op.add_column(sa.Column("ano_orcamento", sa.Integer(), nullable=False))
        if "mes_inicio" not in columns:
            batch_op.add_column(sa.Column("mes_inicio", sa.Integer(), nullable=False))
        if "mes_fim" not in columns:
            batch_op.add_column(sa.Column("mes_fim", sa.Integer(), nullable=False))

        if "created_at" in columns:
            batch_op.alter_column(
                "created_at",
                existing_type=postgresql.TIMESTAMP(),
                nullable=True,
                existing_server_default=sa.text("CURRENT_TIMESTAMP"),
            )

        if "updated_at" in columns:
            batch_op.alter_column(
                "updated_at",
                existing_type=postgresql.TIMESTAMP(),
                nullable=True,
                existing_server_default=sa.text("CURRENT_TIMESTAMP"),
            )

        if "ix_orcamento_cliente_ano_mes" in indexes:
            batch_op.drop_index("ix_orcamento_cliente_ano_mes")
        if "ix_orcamento_cliente_cliente_id" in indexes:
            batch_op.drop_index("ix_orcamento_cliente_cliente_id")
        if "uq_orcamento_cliente_periodo" in uniques:
            batch_op.drop_constraint("uq_orcamento_cliente_periodo", type_="unique")

        if "fk_orcamento_cliente_cliente_id_cliente" in foreign_keys:
            batch_op.drop_constraint(
                "fk_orcamento_cliente_cliente_id_cliente", type_="foreignkey"
            )
            should_create_fk = True

        if should_create_fk:
            batch_op.create_foreign_key(
                batch_op.f("fk_orcamento_cliente_cliente_id_cliente"),
                "cliente",
                ["cliente_id"],
                ["id"],
            )

        legacy_columns = [
            "valor_orcamento_custeio",
            "alerta_ativo_capital",
            "valor_orcamento_capital",
            "alerta_ativo_custeio",
            "percentual_alerta_capital",
            "valor_gasto_custeio",
            "percentual_alerta_custeio",
            "mes",
            "ano",
            "valor_gasto_capital",
            "observacoes",
        ]
        for legacy_column in legacy_columns:
            if legacy_column in columns:
                batch_op.drop_column(legacy_column)

    # ### end Alembic commands ###


def downgrade():
    state = _inspect_orcamento_cliente()
    if not state:
        return

    columns = state["columns"]
    indexes = state["indexes"]
    foreign_keys = state["foreign_keys"]
    uniques = state["uniques"]

    with op.batch_alter_table("orcamento_cliente", schema=None) as batch_op:
        if "valor_total_disponivel" in columns:
            batch_op.drop_column("valor_total_disponivel")
        if "valor_custeio_disponivel" in columns:
            batch_op.drop_column("valor_custeio_disponivel")
        if "valor_capital_disponivel" in columns:
            batch_op.drop_column("valor_capital_disponivel")
        if "valor_alerta_total" in columns:
            batch_op.drop_column("valor_alerta_total")
        if "valor_alerta_custeio" in columns:
            batch_op.drop_column("valor_alerta_custeio")
        if "valor_alerta_capital" in columns:
            batch_op.drop_column("valor_alerta_capital")
        if "ano_orcamento" in columns:
            batch_op.drop_column("ano_orcamento")
        if "mes_inicio" in columns:
            batch_op.drop_column("mes_inicio")
        if "mes_fim" in columns:
            batch_op.drop_column("mes_fim")

        if "created_at" in columns:
            batch_op.alter_column(
                "created_at",
                existing_type=postgresql.TIMESTAMP(),
                nullable=False,
                existing_server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        if "updated_at" in columns:
            batch_op.alter_column(
                "updated_at",
                existing_type=postgresql.TIMESTAMP(),
                nullable=False,
                existing_server_default=sa.text("CURRENT_TIMESTAMP"),
            )

        legacy_columns = [
            sa.Column(
                "valor_orcamento_custeio",
                sa.NUMERIC(precision=15, scale=2),
                nullable=False,
                server_default=sa.text("0.00"),
            ),
            sa.Column(
                "valor_orcamento_capital",
                sa.NUMERIC(precision=15, scale=2),
                nullable=False,
                server_default=sa.text("0.00"),
            ),
            sa.Column(
                "valor_gasto_custeio",
                sa.NUMERIC(precision=15, scale=2),
                nullable=False,
                server_default=sa.text("0.00"),
            ),
            sa.Column(
                "valor_gasto_capital",
                sa.NUMERIC(precision=15, scale=2),
                nullable=False,
                server_default=sa.text("0.00"),
            ),
            sa.Column(
                "percentual_alerta_custeio",
                sa.INTEGER(),
                nullable=False,
                server_default=sa.text("80"),
            ),
            sa.Column(
                "percentual_alerta_capital",
                sa.INTEGER(),
                nullable=False,
                server_default=sa.text("80"),
            ),
            sa.Column(
                "alerta_ativo_custeio",
                sa.BOOLEAN(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "alerta_ativo_capital",
                sa.BOOLEAN(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column("observacoes", sa.TEXT(), nullable=True),
            sa.Column("ano", sa.INTEGER(), nullable=False),
            sa.Column("mes", sa.INTEGER(), nullable=True),
        ]

        for column in legacy_columns:
            if column.name not in columns:
                batch_op.add_column(column)

        if "ix_orcamento_cliente_ano_mes" not in indexes:
            batch_op.create_index(
                "ix_orcamento_cliente_ano_mes", ["ano", "mes"], unique=False
            )
        if "ix_orcamento_cliente_cliente_id" not in indexes:
            batch_op.create_index(
                "ix_orcamento_cliente_cliente_id", ["cliente_id"], unique=False
            )

        if "fk_orcamento_cliente_cliente_id_cliente" in foreign_keys:
            batch_op.drop_constraint(
                "fk_orcamento_cliente_cliente_id_cliente", type_="foreignkey"
            )
        batch_op.create_foreign_key(
            "fk_orcamento_cliente_cliente_id_cliente",
            "cliente",
            ["cliente_id"],
            ["id"],
            ondelete="CASCADE",
        )

        if "uq_orcamento_cliente_periodo" not in uniques:
            batch_op.create_unique_constraint(
                "uq_orcamento_cliente_periodo", ["cliente_id", "ano", "mes"]
            )

    # ### end Alembic commands ###
