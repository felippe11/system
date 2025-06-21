"""Add cliente_id a feedback_campo

Revision ID: ced4f6bf8596
Revises: d7cf3659e660
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "ced4f6bf8596"
down_revision = "d7cf3659e660"
branch_labels = None
depends_on = None

FK_NAME = "fk_feedback_campo_cliente_id"


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # ----- 1) Adiciona a coluna só se ela ainda não existir -----
    cols = [c["name"] for c in insp.get_columns("feedback_campo")]
    if "cliente_id" not in cols:
        op.add_column(
            "feedback_campo",
            sa.Column("cliente_id", sa.Integer(), nullable=True),
        )

    # ----- 2) FK somente fora do SQLite -----
    if bind.dialect.name != "sqlite":
        op.create_foreign_key(
            FK_NAME,
            "feedback_campo",
            "cliente",
            ["cliente_id"],
            ["id"],
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_constraint(FK_NAME, "feedback_campo", type_="foreignkey")

    op.drop_column("feedback_campo", "cliente_id")
