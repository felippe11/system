"""Add voting tables

Revision ID: 8c2f4a9b1e7d
Revises: 7abd8980fd92
Create Date: 2026-02-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8c2f4a9b1e7d"
down_revision = "7abd8980fd92"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "voting_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("evento_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="configuracao",
        ),
        sa.Column("data_inicio_votacao", sa.DateTime(), nullable=True),
        sa.Column("data_fim_votacao", sa.DateTime(), nullable=True),
        sa.Column(
            "exibir_resultados_tempo_real",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "modo_revelacao",
            sa.String(length=20),
            nullable=False,
            server_default="imediato",
        ),
        sa.Column(
            "permitir_votacao_multipla",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "exigir_login_revisor",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "permitir_voto_anonimo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name="fk_voting_event_cliente_id_cliente"),
        sa.ForeignKeyConstraint(["evento_id"], ["evento.id"], name="fk_voting_event_evento_id_evento"),
    )

    op.create_table(
        "voting_category",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("voting_event_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "pontuacao_minima",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "pontuacao_maxima",
            sa.Float(),
            nullable=False,
            server_default="10",
        ),
        sa.Column(
            "tipo_pontuacao",
            sa.String(length=20),
            nullable=False,
            server_default="numerica",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["voting_event_id"],
            ["voting_event.id"],
            name="fk_voting_category_voting_event_id_voting_event",
        ),
    )

    op.create_table(
        "voting_question",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("texto_pergunta", sa.Text(), nullable=False),
        sa.Column("observacao_explicativa", sa.Text(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("obrigatoria", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "tipo_resposta",
            sa.String(length=20),
            nullable=False,
            server_default="numerica",
        ),
        sa.Column("opcoes_resposta", postgresql.JSON, nullable=True),
        sa.Column("valor_minimo", sa.Float(), nullable=True),
        sa.Column("valor_maximo", sa.Float(), nullable=True),
        sa.Column("casas_decimais", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["voting_category.id"],
            name="fk_voting_question_category_id_voting_category",
        ),
    )

    op.create_table(
        "voting_work",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("voting_event_id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("resumo", sa.Text(), nullable=True),
        sa.Column("autores", sa.Text(), nullable=True),
        sa.Column("categoria_original", sa.String(length=255), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ordem_exibicao", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["voting_event_id"],
            ["voting_event.id"],
            name="fk_voting_work_voting_event_id_voting_event",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submission.id"],
            name="fk_voting_work_submission_id_submission",
        ),
    )

    op.create_table(
        "voting_assignment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("voting_event_id", sa.Integer(), nullable=False),
        sa.Column("revisor_id", sa.Integer(), nullable=False),
        sa.Column("work_id", sa.Integer(), nullable=False),
        sa.Column("prazo_votacao", sa.DateTime(), nullable=True),
        sa.Column("concluida", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("data_conclusao", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["voting_event_id"],
            ["voting_event.id"],
            name="fk_voting_assignment_voting_event_id_voting_event",
        ),
        sa.ForeignKeyConstraint(
            ["revisor_id"],
            ["usuario.id"],
            name="fk_voting_assignment_revisor_id_usuario",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["voting_work.id"],
            name="fk_voting_assignment_work_id_voting_work",
        ),
    )

    op.create_table(
        "voting_vote",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("voting_event_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("work_id", sa.Integer(), nullable=False),
        sa.Column("revisor_id", sa.Integer(), nullable=False),
        sa.Column("pontuacao_final", sa.Float(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("data_voto", sa.DateTime(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["voting_event_id"],
            ["voting_event.id"],
            name="fk_voting_vote_voting_event_id_voting_event",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["voting_category.id"],
            name="fk_voting_vote_category_id_voting_category",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["voting_work.id"],
            name="fk_voting_vote_work_id_voting_work",
        ),
        sa.ForeignKeyConstraint(
            ["revisor_id"],
            ["usuario.id"],
            name="fk_voting_vote_revisor_id_usuario",
        ),
    )

    op.create_table(
        "voting_response",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vote_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("valor_numerico", sa.Float(), nullable=True),
        sa.Column("texto_resposta", sa.Text(), nullable=True),
        sa.Column("opcoes_selecionadas", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["vote_id"],
            ["voting_vote.id"],
            name="fk_voting_response_vote_id_voting_vote",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["voting_question.id"],
            name="fk_voting_response_question_id_voting_question",
        ),
    )

    op.create_table(
        "voting_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("voting_event_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("work_id", sa.Integer(), nullable=False),
        sa.Column("pontuacao_total", sa.Float(), nullable=False),
        sa.Column("pontuacao_media", sa.Float(), nullable=False),
        sa.Column("numero_votos", sa.Integer(), nullable=False),
        sa.Column("posicao_ranking", sa.Integer(), nullable=True),
        sa.Column("calculado_em", sa.DateTime(), nullable=True),
        sa.Column("versao_calculo", sa.String(length=20), nullable=False, server_default="1.0"),
        sa.ForeignKeyConstraint(
            ["voting_event_id"],
            ["voting_event.id"],
            name="fk_voting_result_voting_event_id_voting_event",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["voting_category.id"],
            name="fk_voting_result_category_id_voting_category",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["voting_work.id"],
            name="fk_voting_result_work_id_voting_work",
        ),
    )

    op.create_table(
        "voting_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("voting_event_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("acao", sa.String(length=100), nullable=False),
        sa.Column("detalhes", postgresql.JSON, nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("data_acao", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["voting_event_id"],
            ["voting_event.id"],
            name="fk_voting_audit_log_voting_event_id_voting_event",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name="fk_voting_audit_log_usuario_id_usuario",
        ),
    )


def downgrade():
    op.drop_table("voting_audit_log")
    op.drop_table("voting_result")
    op.drop_table("voting_response")
    op.drop_table("voting_vote")
    op.drop_table("voting_assignment")
    op.drop_table("voting_work")
    op.drop_table("voting_question")
    op.drop_table("voting_category")
    op.drop_table("voting_event")
