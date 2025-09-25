"""empty message

Revision ID: 3322b4d6a579
Revises: 997aabdf3c1d
Create Date: 2025-09-22 17:57:16.872757
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3322b4d6a579"
down_revision = "997aabdf3c1d"
branch_labels = None
depends_on = None

# ENUMs como objetos SQLAlchemy SEM criar o TYPE automaticamente
tipo_relatorio_enum = postgresql.ENUM(
    "ATIVIDADE", "MENSAL", "TRIMESTRAL", "ANUAL",
    name="tiporelatorio",
    create_type=False,
)
tipo_campo_enum = postgresql.ENUM(
    "TEXTO", "NUMERO", "DATA", "SELECAO", "MULTIPLA_ESCOLHA", "ARQUIVO", "TEXTO_LONGO",
    name="tipocampo",
    create_type=False,
)

# ------------------------
# Helpers de introspecção
# ------------------------
def _insp():
    return sa.inspect(op.get_bind())

def has_table(name: str) -> bool:
    return name in _insp().get_table_names()

def has_column(table: str, column: str) -> bool:
    insp = _insp()
    try:
        return any(c["name"] == column for c in insp.get_columns(table))
    except Exception:
        return False

def has_fk(table: str, fk_name: str) -> bool:
    try:
        return any(fk.get("name") == fk_name for fk in _insp().get_foreign_keys(table))
    except Exception:
        return False

def _ensure_enums():
    # Garante o TYPE tiporelatorio
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tiporelatorio') THEN
                CREATE TYPE tiporelatorio AS ENUM ('ATIVIDADE','MENSAL','TRIMESTRAL','ANUAL');
            ELSE
                ALTER TYPE tiporelatorio ADD VALUE IF NOT EXISTS 'ATIVIDADE';
                ALTER TYPE tiporelatorio ADD VALUE IF NOT EXISTS 'MENSAL';
                ALTER TYPE tiporelatorio ADD VALUE IF NOT EXISTS 'TRIMESTRAL';
                ALTER TYPE tiporelatorio ADD VALUE IF NOT EXISTS 'ANUAL';
            END IF;
        END
        $$;
        """
    )
    # Garante o TYPE tipocampo
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipocampo') THEN
                CREATE TYPE tipocampo AS ENUM ('TEXTO','NUMERO','DATA','SELECAO','MULTIPLA_ESCOLHA','ARQUIVO','TEXTO_LONGO');
            ELSE
                ALTER TYPE tipocampo ADD VALUE IF NOT EXISTS 'TEXTO';
                ALTER TYPE tipocampo ADD VALUE IF NOT EXISTS 'NUMERO';
                ALTER TYPE tipocampo ADD VALUE IF NOT EXISTS 'DATA';
                ALTER TYPE tipocampo ADD VALUE IF NOT EXISTS 'SELECAO';
                ALTER TYPE tipocampo ADD VALUE IF NOT EXISTS 'MULTIPLA_ESCOLHA';
                ALTER TYPE tipocampo ADD VALUE IF NOT EXISTS 'ARQUIVO';
                ALTER TYPE tipocampo ADD VALUE IF NOT EXISTS 'TEXTO_LONGO';
            END IF;
        END
        $$;
        """
    )


def upgrade():
    _ensure_enums()

    # configuracao_relatorio
    if not has_table("configuracao_relatorio"):
        op.create_table(
            "configuracao_relatorio",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=200), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("tipo", tipo_relatorio_enum, nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=True),
            sa.Column("obrigatorio", sa.Boolean(), nullable=True),
            sa.Column("frequencia_dias", sa.Integer(), nullable=True),
            sa.Column("cliente_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["cliente_id"], ["cliente.id"], name=op.f("fk_configuracao_relatorio_cliente_id_cliente")
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_configuracao_relatorio")),
        )

    # campo_relatorio
    if not has_table("campo_relatorio"):
        op.create_table(
            "campo_relatorio",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column("label", sa.String(length=200), nullable=False),
            sa.Column("tipo", tipo_campo_enum, nullable=False),
            sa.Column("obrigatorio", sa.Boolean(), nullable=True),
            sa.Column("ordem", sa.Integer(), nullable=True),
            sa.Column("opcoes", sa.Text(), nullable=True),
            sa.Column("placeholder", sa.String(length=200), nullable=True),
            sa.Column("validacao", sa.Text(), nullable=True),
            sa.Column("configuracao_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["configuracao_id"], ["configuracao_relatorio.id"],
                name=op.f("fk_campo_relatorio_configuracao_id_configuracao_relatorio"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_campo_relatorio")),
        )

    # categoria_barema
    if not has_table("categoria_barema"):
        op.create_table(
            "categoria_barema",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("evento_id", sa.Integer(), nullable=False),
            sa.Column("categoria", sa.String(length=255), nullable=False),
            sa.Column("nome", sa.String(length=255), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("criterios", sa.JSON(), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["evento_id"], ["evento.id"], name=op.f("fk_categoria_barema_evento_id_evento")
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_categoria_barema")),
        )

    # relatorio_formador_legacy
    if not has_table("relatorio_formador_legacy"):
        op.create_table(
            "relatorio_formador_legacy",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("configuracao_id", sa.Integer(), nullable=False),
            sa.Column("formador_id", sa.Integer(), nullable=False),
            sa.Column("atividade_id", sa.Integer(), nullable=True),
            sa.Column("periodo_inicio", sa.Date(), nullable=True),
            sa.Column("periodo_fim", sa.Date(), nullable=True),
            sa.Column("dados_relatorio", sa.JSON(), nullable=False),
            sa.Column("data_envio", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["atividade_id"], ["oficina.id"], name=op.f("fk_relatorio_formador_legacy_atividade_id_oficina")
            ),
            sa.ForeignKeyConstraint(
                ["configuracao_id"], ["configuracao_relatorio_formador.id"],
                name=op.f("fk_relatorio_formador_legacy_configuracao_id_configuracao_relatorio_formador"),
            ),
            sa.ForeignKeyConstraint(
                ["formador_id"], ["ministrante.id"], name=op.f("fk_relatorio_formador_legacy_formador_id_ministrante")
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_relatorio_formador_legacy")),
        )

    # historico_relatorio
    if not has_table("historico_relatorio"):
        op.create_table(
            "historico_relatorio",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("relatorio_id", sa.Integer(), nullable=False),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("usuario_tipo", sa.String(length=20), nullable=False),
            sa.Column("acao", sa.String(length=50), nullable=False),
            sa.Column("detalhes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["relatorio_id"], ["relatorio_formador.id"],
                name=op.f("fk_historico_relatorio_relatorio_id_relatorio_formador"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_historico_relatorio")),
        )

    # resposta_campo
    if not has_table("resposta_campo"):
        op.create_table(
            "resposta_campo",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("relatorio_id", sa.Integer(), nullable=False),
            sa.Column("campo_id", sa.Integer(), nullable=False),
            sa.Column("valor", sa.Text(), nullable=True),
            sa.Column("arquivo_path", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["campo_id"], ["campo_relatorio.id"], name=op.f("fk_resposta_campo_campo_id_campo_relatorio")
            ),
            sa.ForeignKeyConstraint(
                ["relatorio_id"], ["relatorio_formador.id"], name=op.f("fk_resposta_campo_relatorio_id_relatorio_formador")
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_resposta_campo")),
        )

    # teste_barema
    if not has_table("teste_barema"):
        op.create_table(
            "teste_barema",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("barema_id", sa.Integer(), nullable=False),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("pontuacoes", sa.JSON(), nullable=False),
            sa.Column("total_pontos", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["barema_id"], ["categoria_barema.id"], name=op.f("fk_teste_barema_barema_id_categoria_barema")
            ),
            sa.ForeignKeyConstraint(
                ["usuario_id"], ["usuario.id"], name=op.f("fk_teste_barema_usuario_id_usuario")
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_teste_barema")),
        )

    # avaliacao_barema
    if not has_table("avaliacao_barema"):
        op.create_table(
            "avaliacao_barema",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("trabalho_id", sa.Integer(), nullable=False),
            sa.Column("revisor_id", sa.Integer(), nullable=False),
            sa.Column("barema_id", sa.Integer(), nullable=False),
            sa.Column("categoria", sa.String(length=255), nullable=False),
            sa.Column("nota_final", sa.Float(), nullable=True),
            sa.Column("data_avaliacao", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["revisor_id"], ["usuario.id"], name=op.f("fk_avaliacao_barema_revisor_id_usuario")
            ),
            sa.ForeignKeyConstraint(
                ["trabalho_id"], ["submission.id"], name=op.f("fk_avaliacao_barema_trabalho_id_submission")
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_avaliacao_barema")),
        )

    # avaliacao_criterio
    if not has_table("avaliacao_criterio"):
        op.create_table(
            "avaliacao_criterio",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("avaliacao_id", sa.Integer(), nullable=False),
            sa.Column("criterio_id", sa.String(length=255), nullable=False),
            sa.Column("nota", sa.Float(), nullable=False),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["avaliacao_id"], ["avaliacao_barema.id"], name=op.f("fk_avaliacao_criterio_avaliacao_id_avaliacao_barema")
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_avaliacao_criterio")),
        )

    # material: add fornecedor (se ainda não existir)
    if has_table("material") and not has_column("material", "fornecedor"):
        with op.batch_alter_table("material", schema=None) as batch_op:
            batch_op.add_column(sa.Column("fornecedor", sa.String(length=255), nullable=True))

    # monitor_cadastro_link: add usage_count (com default 0 para não quebrar dados), dropar used
    if has_table("monitor_cadastro_link"):
        need_usage = not has_column("monitor_cadastro_link", "usage_count")
        has_used = has_column("monitor_cadastro_link", "used")
        if need_usage or has_used:
            with op.batch_alter_table("monitor_cadastro_link", schema=None) as batch_op:
                if need_usage:
                    batch_op.add_column(sa.Column("usage_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
                if has_used:
                    try:
                        batch_op.drop_column("used")
                    except Exception:
                        pass
            # retirar server_default se acabamos de adicioná-lo
            if need_usage:
                try:
                    with op.batch_alter_table("monitor_cadastro_link", schema=None) as batch_op:
                        batch_op.alter_column("usage_count", server_default=None)
                except Exception:
                    pass

    # relatorio_formador: colunas/FKs/alterações tolerantes
    if has_table("relatorio_formador"):
        fk_cfg_new = "fk_relatorio_formador_configuracao_id_configuracao_relatorio"
        fk_ofi_new = "fk_relatorio_formador_oficina_id_oficina"
        fk_cfg_old = "fk_relatorio_formador_configuracao_id_configuracao_rela_e433"
        fk_ofi_old = "fk_relatorio_formador_atividade_id_oficina"

        with op.batch_alter_table("relatorio_formador", schema=None) as batch_op:
            # colunas novas
            if not has_column("relatorio_formador", "oficina_id"):
                batch_op.add_column(sa.Column("oficina_id", sa.Integer(), nullable=True))
            if not has_column("relatorio_formador", "status"):
                batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=True))
            if not has_column("relatorio_formador", "observacoes_cliente"):
                batch_op.add_column(sa.Column("observacoes_cliente", sa.Text(), nullable=True))
            if not has_column("relatorio_formador", "data_aprovacao"):
                batch_op.add_column(sa.Column("data_aprovacao", sa.DateTime(), nullable=True))
            if not has_column("relatorio_formador", "created_at"):
                batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
            if not has_column("relatorio_formador", "updated_at"):
                batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

            # alterações de tipo tolerantes
            try:
                batch_op.alter_column("periodo_inicio", existing_type=sa.DATE(), type_=sa.DateTime(), existing_nullable=True)
            except Exception:
                pass
            try:
                batch_op.alter_column("periodo_fim", existing_type=sa.DATE(), type_=sa.DateTime(), existing_nullable=True)
            except Exception:
                pass
            try:
                batch_op.alter_column("data_envio", existing_type=postgresql.TIMESTAMP(), nullable=True)
            except Exception:
                pass

            # FKs antigas -> remover se existirem
            if has_fk("relatorio_formador", fk_ofi_old):
                try:
                    batch_op.drop_constraint(fk_ofi_old, type_="foreignkey")
                except Exception:
                    pass
            if has_fk("relatorio_formador", fk_cfg_old):
                try:
                    batch_op.drop_constraint(fk_cfg_old, type_="foreignkey")
                except Exception:
                    pass

            # FKs novas -> criar só se não existirem
            if not has_fk("relatorio_formador", fk_ofi_new):
                batch_op.create_foreign_key(fk_ofi_new, "oficina", ["oficina_id"], ["id"])
            if not has_fk("relatorio_formador", fk_cfg_new):
                batch_op.create_foreign_key(fk_cfg_new, "configuracao_relatorio", ["configuracao_id"], ["id"])

            # remover colunas antigas se existirem
            if has_column("relatorio_formador", "atividade_id"):
                try:
                    batch_op.drop_column("atividade_id")
                except Exception:
                    pass
            if has_column("relatorio_formador", "dados_relatorio"):
                try:
                    batch_op.drop_column("dados_relatorio")
                except Exception:
                    pass


def downgrade():
    # relatorio_formador rollback
    if has_table("relatorio_formador"):
        with op.batch_alter_table("relatorio_formador", schema=None) as batch_op:
            if not has_column("relatorio_formador", "dados_relatorio"):
                batch_op.add_column(sa.Column("dados_relatorio", postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False))
            if not has_column("relatorio_formador", "atividade_id"):
                batch_op.add_column(sa.Column("atividade_id", sa.INTEGER(), autoincrement=False, nullable=True))

            try:
                batch_op.drop_constraint("fk_relatorio_formador_configuracao_id_configuracao_relatorio", type_="foreignkey")
            except Exception:
                pass
            try:
                batch_op.drop_constraint("fk_relatorio_formador_oficina_id_oficina", type_="foreignkey")
            except Exception:
                pass

            if not has_fk("relatorio_formador", "fk_relatorio_formador_configuracao_id_configuracao_rela_e433"):
                try:
                    batch_op.create_foreign_key("fk_relatorio_formador_configuracao_id_configuracao_rela_e433", "configuracao_relatorio_formador", ["configuracao_id"], ["id"])
                except Exception:
                    pass
            if not has_fk("relatorio_formador", "fk_relatorio_formador_atividade_id_oficina"):
                try:
                    batch_op.create_foreign_key("fk_relatorio_formador_atividade_id_oficina", "oficina", ["atividade_id"], ["id"])
                except Exception:
                    pass

            try:
                batch_op.alter_column("data_envio", existing_type=postgresql.TIMESTAMP(), nullable=False)
            except Exception:
                pass
            try:
                batch_op.alter_column("periodo_fim", existing_type=sa.DateTime(), type_=sa.DATE(), existing_nullable=True)
            except Exception:
                pass
            try:
                batch_op.alter_column("periodo_inicio", existing_type=sa.DateTime(), type_=sa.DATE(), existing_nullable=True)
            except Exception:
                pass

            for col in ["updated_at", "created_at", "data_aprovacao", "observacoes_cliente", "status", "oficina_id"]:
                if has_column("relatorio_formador", col):
                    try:
                        batch_op.drop_column(col)
                    except Exception:
                        pass

    # monitor_cadastro_link rollback
    if has_table("monitor_cadastro_link"):
        with op.batch_alter_table("monitor_cadastro_link", schema=None) as batch_op:
            if not has_column("monitor_cadastro_link", "used"):
                try:
                    batch_op.add_column(sa.Column("used", sa.BOOLEAN(), autoincrement=False, nullable=True))
                except Exception:
                    pass
            if has_column("monitor_cadastro_link", "usage_count"):
                try:
                    batch_op.drop_column("usage_count")
                except Exception:
                    pass

    # material rollback
    if has_table("material") and has_column("material", "fornecedor"):
        with op.batch_alter_table("material", schema=None) as batch_op:
            try:
                batch_op.drop_column("fornecedor")
            except Exception:
                pass

    # dropar tabelas criadas (somente se existirem)
    for tbl in [
        "avaliacao_criterio",
        "avaliacao_barema",
        "teste_barema",
        "resposta_campo",
        "historico_relatorio",
        "relatorio_formador_legacy",
        "categoria_barema",
        "campo_relatorio",
        "configuracao_relatorio",
    ]:
        if has_table(tbl):
            try:
                op.drop_table(tbl)
            except Exception:
                pass
