"""empty message

Revision ID: 0526210919ba
Revises: a74fa7e7d502
Create Date: 2025-08-26 11:46:37.841518
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0526210919ba"
down_revision = "a74fa7e7d502"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Cria a tabela nova (inalterada)
    op.create_table(
        "acesso_validacao_certificado",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("certificado_id", sa.Integer(), nullable=False),
        sa.Column("data_acesso", sa.DateTime(), nullable=False),
        sa.Column("ip_acesso", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["certificado_id"],
            ["certificado_participante.id"],
            name=op.f(
                "fk_acesso_validacao_certificado_certificado_id_certificado_participante"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acesso_validacao_certificado")),
    )

    # 2) BACKFILL em revisor_candidatura SEM JOIN
    # - nome: mantém se já tiver; senão tenta prefixo do email; senão "Sem nome"
    op.execute(
        """
        UPDATE revisor_candidatura
        SET nome = COALESCE(
            NULLIF(btrim(nome), ''),
            NULLIF(split_part(btrim(email), '@', 1), ''),
            'Sem nome'
        )
        WHERE nome IS NULL OR btrim(nome) = '';
        """
    )

    # - email: mantém se já tiver; senão placeholder
    op.execute(
        """
        UPDATE revisor_candidatura
        SET email = COALESCE(
            NULLIF(btrim(email), ''),
            'sem-email@placeholder.local'
        )
        WHERE email IS NULL OR btrim(email) = '';
        """
    )

    # 3) Agora aplicar NOT NULL
    with op.batch_alter_table("revisor_candidatura", schema=None) as batch_op:
        batch_op.alter_column(
            "nome",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            nullable=False,
        )

    # (Opcional) Evita strings vazias no futuro com CHECKs
    # op.create_check_constraint(
    #     "revisor_candidatura_nome_not_blank",
    #     "revisor_candidatura",
    #     "btrim(nome) <> ''"
    # )
    # op.create_check_constraint(
    #     "revisor_candidatura_email_not_blank",
    #     "revisor_candidatura",
    #     "btrim(email) <> ''"
    # )


def downgrade():
    with op.batch_alter_table("revisor_candidatura", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            nullable=True,
        )
        batch_op.alter_column(
            "nome",
            existing_type=sa.String(length=255),
            nullable=True,
        )

    op.drop_table("acesso_validacao_certificado")
