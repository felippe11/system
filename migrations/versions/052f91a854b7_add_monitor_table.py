"""add monitor table

Revision ID: 052f91a854b7
Revises: 36a58e54b28a
Create Date: 2025-08-23 12:45:51.732083
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "052f91a854b7"
down_revision = "36a58e54b28a"
branch_labels = None
depends_on = None


# ------------------------------- #
# Helpers para idempotência
# ------------------------------- #
def _insp():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _insp().has_table(name)


def _has_column(table: str, col: str) -> bool:
    insp = _insp()
    if not insp.has_table(table):
        return False
    return any(c["name"] == col for c in insp.get_columns(table))


def _has_fk(table: str, fk_name: str) -> bool:
    insp = _insp()
    if not insp.has_table(table):
        return False
    try:
        return any(fk.get("name") == fk_name for fk in insp.get_foreign_keys(table))
    except Exception:
        return False


def _has_fk_prefix(table: str, prefix: str) -> bool:
    """Alguns nomes de FK recebem sufixo hash pelo naming_convention.
    Verifica por prefixo para evitar recriações indevidas.
    """
    insp = _insp()
    if not insp.has_table(table):
        return False
    try:
        for fk in insp.get_foreign_keys(table):
            name = fk.get("name") or ""
            if name.startswith(prefix):
                return True
        return False
    except Exception:
        return False


def _has_unique(table: str, name: str) -> bool:
    insp = _insp()
    if not insp.has_table(table):
        return False
    try:
        return any(uq.get("name") == name for uq in insp.get_unique_constraints(table))
    except Exception:
        return False


def upgrade():
    # --- monitor
    if not _has_table("monitor"):
        op.create_table(
            "monitor",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome_completo", sa.String(length=255), nullable=False),
            sa.Column("curso", sa.String(length=255), nullable=False),
            sa.Column("carga_horaria_disponibilidade", sa.Integer(), nullable=False),
            sa.Column("dias_disponibilidade", sa.String(length=255), nullable=False),
            sa.Column("turnos_disponibilidade", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("telefone_whatsapp", sa.String(length=20), nullable=False),
            sa.Column("codigo_acesso", sa.String(length=10), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("cliente_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["cliente_id"], ["cliente.id"], name=op.f("fk_monitor_cliente_id_cliente")
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_monitor")),
            sa.UniqueConstraint("codigo_acesso", name=op.f("uq_monitor_codigo_acesso")),
            sa.UniqueConstraint("email", name=op.f("uq_monitor_email")),
        )

    # --- revisor_process_evento (pode já existir)
    if not _has_table("revisor_process_evento"):
        op.create_table(
            "revisor_process_evento",
            sa.Column("process_id", sa.Integer(), nullable=False),
            sa.Column("evento_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["evento_id"],
                ["evento.id"],
                name=op.f("fk_revisor_process_evento_evento_id_evento"),
            ),
            sa.ForeignKeyConstraint(
                ["process_id"],
                ["revisor_process.id"],
                name=op.f("fk_revisor_process_evento_process_id_revisor_process"),
            ),
            sa.PrimaryKeyConstraint(
                "process_id", "evento_id", name=op.f("pk_revisor_process_evento")
            ),
        )
    else:
        # Garante FKs com nomes esperados
        if not _has_fk(
            "revisor_process_evento", op.f("fk_revisor_process_evento_evento_id_evento")
        ):
            op.create_foreign_key(
                op.f("fk_revisor_process_evento_evento_id_evento"),
                "revisor_process_evento",
                "evento",
                ["evento_id"],
                ["id"],
            )
        if not _has_fk(
            "revisor_process_evento",
            op.f("fk_revisor_process_evento_process_id_revisor_process"),
        ):
            op.create_foreign_key(
                op.f("fk_revisor_process_evento_process_id_revisor_process"),
                "revisor_process_evento",
                "revisor_process",
                ["process_id"],
                ["id"],
            )

    # --- participante_evento
    if not _has_table("participante_evento"):
        op.create_table(
            "participante_evento",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("evento_id", sa.Integer(), nullable=False),
            sa.Column("data_inscricao", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=True),
            sa.ForeignKeyConstraint(
                ["evento_id"],
                ["evento.id"],
                name=op.f("fk_participante_evento_evento_id_evento"),
            ),
            sa.ForeignKeyConstraint(
                ["usuario_id"],
                ["usuario.id"],
                name=op.f("fk_participante_evento_usuario_id_usuario"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_participante_evento")),
        )

    # --- monitor_agendamento
    if not _has_table("monitor_agendamento"):
        op.create_table(
            "monitor_agendamento",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("monitor_id", sa.Integer(), nullable=False),
            sa.Column("agendamento_id", sa.Integer(), nullable=False),
            sa.Column("data_atribuicao", sa.DateTime(), nullable=True),
            sa.Column("tipo_distribuicao", sa.String(length=20), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["agendamento_id"],
                ["agendamento_visita.id"],
                name=op.f("fk_monitor_agendamento_agendamento_id_agendamento_visita"),
            ),
            sa.ForeignKeyConstraint(
                ["monitor_id"],
                ["monitor.id"],
                name=op.f("fk_monitor_agendamento_monitor_id_monitor"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_monitor_agendamento")),
        )

    # --- presenca_aluno
    if not _has_table("presenca_aluno"):
        op.create_table(
            "presenca_aluno",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("aluno_id", sa.Integer(), nullable=False),
            sa.Column("monitor_id", sa.Integer(), nullable=False),
            sa.Column("agendamento_id", sa.Integer(), nullable=False),
            sa.Column("presente", sa.Boolean(), nullable=True),
            sa.Column("data_registro", sa.DateTime(), nullable=True),
            sa.Column("metodo_confirmacao", sa.String(length=20), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["agendamento_id"],
                ["agendamento_visita.id"],
                name=op.f("fk_presenca_aluno_agendamento_id_agendamento_visita"),
            ),
            sa.ForeignKeyConstraint(
                ["aluno_id"],
                ["aluno_visitante.id"],
                name=op.f("fk_presenca_aluno_aluno_id_aluno_visitante"),
            ),
            sa.ForeignKeyConstraint(
                ["monitor_id"],
                ["monitor.id"],
                name=op.f("fk_presenca_aluno_monitor_id_monitor"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_presenca_aluno")),
        )

    # --- review_email_log (drop se existir)
    if _has_table("review_email_log"):
        op.drop_table("review_email_log")

    # --- evento_barema: dropar unique se existir
    if _has_table("evento_barema") and _has_unique(
        "evento_barema", "uq_evento_barema_evento_id"
    ):
        with op.batch_alter_table("evento_barema", schema=None) as batch_op:
            batch_op.drop_constraint("uq_evento_barema_evento_id", type_="unique")

    # --- formularios: alterar nullable (seguro mesmo se já estiver True)
    if _has_table("formularios") and _has_column("formularios", "is_submission_form"):
        with op.batch_alter_table("formularios", schema=None) as batch_op:
            batch_op.alter_column(
                "is_submission_form",
                existing_type=sa.BOOLEAN(),
                nullable=True,
                existing_server_default=sa.text("false"),
            )

    # --- revisor_process: add evento_id + FK se faltarem
    if _has_table("revisor_process"):
        if not _has_column("revisor_process", "evento_id"):
            with op.batch_alter_table("revisor_process", schema=None) as batch_op:
                batch_op.add_column(sa.Column("evento_id", sa.Integer(), nullable=True))
        if not _has_fk("revisor_process", op.f("fk_revisor_process_evento_id_evento")):
            with op.batch_alter_table("revisor_process", schema=None) as batch_op:
                batch_op.create_foreign_key(
                    batch_op.f("fk_revisor_process_evento_id_evento"),
                    "evento",
                    ["evento_id"],
                    ["id"],
                )

    # --- revisor_process_evento_association: renomeio de FK/coluna
    if _has_table("revisor_process_evento_association"):
        with op.batch_alter_table(
            "revisor_process_evento_association", schema=None
        ) as batch_op:
            if not _has_column(
                "revisor_process_evento_association", "revisor_process_id"
            ):
                batch_op.add_column(
                    sa.Column("revisor_process_id", sa.Integer(), nullable=False)
                )

            # drop FK antiga se existir (nome antigo, sem hash)
            if _has_fk(
                "revisor_process_evento_association",
                "fk_revisor_process_evento_association_process_id_reviso_3fff",
            ):
                batch_op.drop_constraint(
                    "fk_revisor_process_evento_association_process_id_reviso_3fff",
                    type_="foreignkey",
                )

            # cria a nova FK se ainda não existir (checando por prefixo por causa do hash)
            _new_fk_prefix = "fk_revisor_process_evento_association_revisor_process_i"
            if not _has_fk_prefix(
                "revisor_process_evento_association", _new_fk_prefix
            ):
                batch_op.create_foreign_key(
                    batch_op.f(
                        "fk_revisor_process_evento_association_revisor_process_id_revisor_process"
                    ),
                    "revisor_process",
                    ["revisor_process_id"],
                    ["id"],
                )

            if _has_column("revisor_process_evento_association", "process_id"):
                batch_op.drop_column("process_id")

    # --- submission: add attributes JSON se faltar
    if _has_table("submission") and not _has_column("submission", "attributes"):
        with op.batch_alter_table("submission", schema=None) as batch_op:
            batch_op.add_column(sa.Column("attributes", sa.JSON(), nullable=True))

    # --- work_metadata: add data JSON se faltar
    if _has_table("work_metadata") and not _has_column("work_metadata", "data"):
        # Se a tabela já tiver linhas, adicionar como nullable=True evita erro de NOT NULL
        with op.batch_alter_table("work_metadata", schema=None) as batch_op:
            batch_op.add_column(sa.Column("data", sa.JSON(), nullable=True))


def downgrade():
    # Reverte com segurança (só se existir)

    if _has_table("work_metadata") and _has_column("work_metadata", "data"):
        with op.batch_alter_table("work_metadata", schema=None) as batch_op:
            batch_op.drop_column("data")

    if _has_table("submission") and _has_column("submission", "attributes"):
        with op.batch_alter_table("submission", schema=None) as batch_op:
            batch_op.drop_column("attributes")

    if _has_table("revisor_process_evento_association"):
        with op.batch_alter_table(
            "revisor_process_evento_association", schema=None
        ) as batch_op:
            if not _has_column("revisor_process_evento_association", "process_id"):
                batch_op.add_column(
                    sa.Column(
                        "process_id",
                        sa.INTEGER(),
                        autoincrement=False,
                        nullable=False,
                    )
                )
            if _has_fk(
                "revisor_process_evento_association",
                batch_op.f(
                    "fk_revisor_process_evento_association_revisor_process_id_revisor_process"
                ),
            ):
                batch_op.drop_constraint(
                    batch_op.f(
                        "fk_revisor_process_evento_association_revisor_process_id_revisor_process"
                    ),
                    type_="foreignkey",
                )
            if not _has_fk(
                "revisor_process_evento_association",
                "fk_revisor_process_evento_association_process_id_reviso_3fff",
            ):
                batch_op.create_foreign_key(
                    "fk_revisor_process_evento_association_process_id_reviso_3fff",
                    "revisor_process",
                    ["process_id"],
                    ["id"],
                )
            if _has_column("revisor_process_evento_association", "revisor_process_id"):
                batch_op.drop_column("revisor_process_id")

    if _has_table("revisor_process"):
        with op.batch_alter_table("revisor_process", schema=None) as batch_op:
            if _has_fk(
                "revisor_process", batch_op.f("fk_revisor_process_evento_id_evento")
            ):
                batch_op.drop_constraint(
                    batch_op.f("fk_revisor_process_evento_id_evento"),
                    type_="foreignkey",
                )
            if _has_column("revisor_process", "evento_id"):
                batch_op.drop_column("evento_id")

    if _has_table("formularios") and _has_column("formularios", "is_submission_form"):
        with op.batch_alter_table("formularios", schema=None) as batch_op:
            batch_op.alter_column(
                "is_submission_form",
                existing_type=sa.BOOLEAN(),
                nullable=False,
                existing_server_default=sa.text("false"),
            )

    if _has_table("evento_barema") and not _has_unique(
        "evento_barema", "uq_evento_barema_evento_id"
    ):
        with op.batch_alter_table("evento_barema", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                "uq_evento_barema_evento_id", ["evento_id"]
            )

    # recria review_email_log se tiver sido dropada
    if not _has_table("review_email_log"):
        op.create_table(
            "review_email_log",
            sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
            sa.Column("review_id", sa.INTEGER(), autoincrement=False, nullable=False),
            sa.Column("recipient", sa.VARCHAR(length=255), autoincrement=False, nullable=False),
            sa.Column("error", sa.VARCHAR(length=255), autoincrement=False, nullable=True),
            sa.Column(
                "created_at",
                postgresql.TIMESTAMP(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                autoincrement=False,
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["review_id"], ["review.id"], name="fk_review_email_log_review_id_review"
            ),
            sa.PrimaryKeyConstraint("id", name="pk_review_email_log"),
        )

    if _has_table("presenca_aluno"):
        op.drop_table("presenca_aluno")

    if _has_table("monitor_agendamento"):
        op.drop_table("monitor_agendamento")

    if _has_table("participante_evento"):
        op.drop_table("participante_evento")

    if _has_table("revisor_process_evento"):
        op.drop_table("revisor_process_evento")

    if _has_table("monitor"):
        op.drop_table("monitor")
