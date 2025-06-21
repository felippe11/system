"""Add num_vencedores column to sorteio table + cliente_id em feedback_campo

Revision ID: 6cffbe38b1e8
Revises: b3b7d1f9bcb2
Create Date: 2025-05-11 23:47:21.432094
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "6cffbe38b1e8"
down_revision = "b3b7d1f9bcb2"
branch_labels = None
depends_on = None


# --------------------------------------------------------------------------- #
# UPGRADE
# --------------------------------------------------------------------------- #
def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # 1) Apaga tabela proposta somente se existir
    if "proposta" in insp.get_table_names():
        op.drop_table("proposta")

    # 2) feedback_campo ─ adiciona cliente_id e torna ministrante_id opcional
    with op.batch_alter_table("feedback_campo") as batch:
        if "cliente_id" not in [c["name"] for c in insp.get_columns("feedback_campo")]:
            batch.add_column(sa.Column("cliente_id", sa.Integer(), nullable=True))

        batch.alter_column("ministrante_id",
                           existing_type=sa.INTEGER(),
                           nullable=True)

    op.create_foreign_key(
        "fk_feedback_campo_cliente_id_cliente",
        "feedback_campo",
        "cliente",
        ["cliente_id"], ["id"],
    )

    # 3) sorteio ─ adiciona num_vencedores
    with op.batch_alter_table("sorteio") as batch:
        if "num_vencedores" not in [c["name"] for c in insp.get_columns("sorteio")]:
            batch.add_column(sa.Column("num_vencedores", sa.Integer(), nullable=True))


# --------------------------------------------------------------------------- #
# DOWNGRADE
# --------------------------------------------------------------------------- #
def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # 1) Reverte sorteio
    if "num_vencedores" in [c["name"] for c in insp.get_columns("sorteio")]:
        with op.batch_alter_table("sorteio") as batch:
            batch.drop_column("num_vencedores")

    # 2) Reverte feedback_campo
    if "fk_feedback_campo_cliente_id_cliente" in [
        fk["name"] for fk in insp.get_foreign_keys("feedback_campo")
    ]:
        op.drop_constraint(
            "fk_feedback_campo_cliente_id_cliente",
            "feedback_campo",
            type_="foreignkey",
        )

    with op.batch_alter_table("feedback_campo") as batch:
        batch.alter_column("ministrante_id",
                           existing_type=sa.INTEGER(),
                           nullable=False)
        if "cliente_id" in [c["name"] for c in insp.get_columns("feedback_campo")]:
            batch.drop_column("cliente_id")

    # 3) Restaura proposta
    if "proposta" not in insp.get_table_names():
        op.create_table(
            "proposta",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nome", sa.String(150)),
            sa.Column("email", sa.String(150), nullable=False),
            sa.Column("tipo_evento", sa.String(50), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=False),
            sa.Column("data_submissao", postgresql.TIMESTAMP()),
            sa.Column("status", sa.String(20)),
        )
