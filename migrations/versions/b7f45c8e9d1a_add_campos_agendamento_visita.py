"""add campos agendamento visita

Revision ID: b7f45c8e9d1a
Revises: 6d0c1bfa2e5b, b460e470d7a9, f0c6022a4f5a
Create Date: 2025-08-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "b7f45c8e9d1a"
down_revision = ("6d0c1bfa2e5b", "b460e470d7a9", "f0c6022a4f5a")
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agendamento_visita") as batch_op:
        batch_op.add_column(sa.Column("rede_ensino", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("municipio", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("bairro", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("responsavel_nome", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("responsavel_cargo", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("responsavel_whatsapp", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("responsavel_email", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("acompanhantes_nomes", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("acompanhantes_qtd", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("precisa_transporte", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("observacoes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("compromisso_1", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("compromisso_2", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("compromisso_3", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("compromisso_4", sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("agendamento_visita") as batch_op:
        batch_op.drop_column("compromisso_4")
        batch_op.drop_column("compromisso_3")
        batch_op.drop_column("compromisso_2")
        batch_op.drop_column("compromisso_1")
        batch_op.drop_column("observacoes")
        batch_op.drop_column("precisa_transporte")
        batch_op.drop_column("acompanhantes_qtd")
        batch_op.drop_column("acompanhantes_nomes")
        batch_op.drop_column("responsavel_email")
        batch_op.drop_column("responsavel_whatsapp")
        batch_op.drop_column("responsavel_cargo")
        batch_op.drop_column("responsavel_nome")
        batch_op.drop_column("bairro")
        batch_op.drop_column("municipio")
        batch_op.drop_column("rede_ensino")
