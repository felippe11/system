"""empty message

Revision ID: 5ffe4399fa5b
Revises: c439cf81f64a
Create Date: 2025-09-17 19:38:34.717438
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5ffe4399fa5b"
down_revision = "c439cf81f64a"
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
    bind = op.get_bind()

    # ---- nivel_aprovacao (evita recriação) ----
    if not _table_exists(bind, "nivel_aprovacao"):
        op.create_table(
            "nivel_aprovacao",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("ordem", sa.Integer(), nullable=False),
            sa.Column("valor_minimo", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("valor_maximo", sa.Float(), nullable=True),
            sa.Column("obrigatorio", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("cliente_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name=op.f("fk_nivel_aprovacao_cliente_id_cliente")),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_nivel_aprovacao")),
        )

    # ---- orcamento_cliente (evita recriação) ----
    if not _table_exists(bind, "orcamento_cliente"):
        op.create_table(
            "orcamento_cliente",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cliente_id", sa.Integer(), nullable=False),
            sa.Column("valor_total_disponivel", sa.Float(), nullable=False),
            sa.Column("valor_custeio_disponivel", sa.Float(), nullable=False),
            sa.Column("valor_capital_disponivel", sa.Float(), nullable=False),
            sa.Column("valor_alerta_total", sa.Float(), nullable=False),
            sa.Column("valor_alerta_custeio", sa.Float(), nullable=False),
            sa.Column("valor_alerta_capital", sa.Float(), nullable=False),
            sa.Column("ano_orcamento", sa.Integer(), nullable=False),
            sa.Column("mes_inicio", sa.Integer(), nullable=False),
            sa.Column("mes_fim", sa.Integer(), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name=op.f("fk_orcamento_cliente_cliente_id_cliente")),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_orcamento_cliente")),
        )

    # ---- orcamento (evita recriação) ----
    if not _table_exists(bind, "orcamento"):
        op.create_table(
            "orcamento",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("polo_id", sa.Integer(), nullable=False),
            sa.Column("valor_total", sa.Float(), nullable=False),
            sa.Column("valor_custeio", sa.Float(), nullable=False),
            sa.Column("valor_capital", sa.Float(), nullable=False),
            sa.Column("data_inicio", sa.Date(), nullable=False),
            sa.Column("data_fim", sa.Date(), nullable=False),
            sa.Column("ano_orcamento", sa.Integer(), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["polo_id"], ["polo.id"], name=op.f("fk_orcamento_polo_id_polo")),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_orcamento")),
        )

    # ---- historico_orcamento (evita recriação) ----
    if not _table_exists(bind, "historico_orcamento"):
        op.create_table(
            "historico_orcamento",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("orcamento_id", sa.Integer(), nullable=False),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("tipo_alteracao", sa.String(length=50), nullable=False),
            sa.Column("valor_total_anterior", sa.Float(), nullable=True),
            sa.Column("valor_custeio_anterior", sa.Float(), nullable=True),
            sa.Column("valor_capital_anterior", sa.Float(), nullable=True),
            sa.Column("valor_total_novo", sa.Float(), nullable=True),
            sa.Column("valor_custeio_novo", sa.Float(), nullable=True),
            sa.Column("valor_capital_novo", sa.Float(), nullable=True),
            sa.Column("motivo", sa.Text(), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("data_alteracao", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["orcamento_id"], ["orcamento.id"], name=op.f("fk_historico_orcamento_orcamento_id_orcamento")),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], name=op.f("fk_historico_orcamento_usuario_id_usuario")),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_historico_orcamento")),
        )

    # ---- aprovacao_compra (evita recriação) ----
    # Garante dependências mínimas
    if not _table_exists(bind, "compra"):
        raise RuntimeError(
            "Tabela 'compra' não existe. Verifique a cadeia de migrações para que 'compra' seja criada antes desta revisão."
        )
    if not _table_exists(bind, "nivel_aprovacao"):
        raise RuntimeError(
            "Tabela 'nivel_aprovacao' não existe. Verifique a cadeia de migrações para que 'nivel_aprovacao' seja criada antes desta revisão."
        )

    if not _table_exists(bind, "aprovacao_compra"):
        op.create_table(
            "aprovacao_compra",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pendente"),
            sa.Column("comentario", sa.Text(), nullable=True),
            sa.Column("data_aprovacao", sa.DateTime(), nullable=True),
            sa.Column("compra_id", sa.Integer(), nullable=False),
            sa.Column("nivel_aprovacao_id", sa.Integer(), nullable=False),
            sa.Column("aprovador_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["aprovador_id"], ["usuario.id"], name=op.f("fk_aprovacao_compra_aprovador_id_usuario")),
            sa.ForeignKeyConstraint(["compra_id"], ["compra.id"], name=op.f("fk_aprovacao_compra_compra_id_compra")),
            sa.ForeignKeyConstraint(["nivel_aprovacao_id"], ["nivel_aprovacao.id"], name=op.f("fk_aprovacao_compra_nivel_aprovacao_id_nivel_aprovacao")),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_aprovacao_compra")),
        )

    # ---- compra.tipo_gasto (evita coluna duplicada) ----
    if not _column_exists(bind, "compra", "tipo_gasto"):
        op.add_column(
            "compra",
            sa.Column("tipo_gasto", sa.String(length=20), nullable=False, server_default="custeio"),
        )
        # Remove default do schema após popular linhas existentes
        op.alter_column("compra", "tipo_gasto", server_default=None)


def downgrade():
    # No-op: esta revisão foi tornada idempotente e não deve remover objetos
    # que podem ter sido criados por migrações anteriores.
    pass
