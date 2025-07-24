"""Add password reset token table (idempotente)

Revision ID: 9bac7f9f0073
Revises: a5154a3f3a4c
Create Date: 2025‑07‑20 04:08:13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "9bac7f9f0073"
down_revision = "a5154a3f3a4c"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # ---------- 1) Cria a tabela se ela ainda não existir ----------
    if "password_reset_token" not in insp.get_table_names():
        op.create_table(
            "password_reset_token",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "usuario_id",
                sa.Integer(),
                sa.ForeignKey("usuario.id"),
                nullable=False,
            ),
            sa.Column("token", sa.String(length=36), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=True),
        )
        return  # nada mais a fazer

    # ---------- 2) Se já existir, garante a consistência ----------
    cols = {c["name"] for c in insp.get_columns("password_reset_token")}

    if "used" not in cols:
        op.add_column("password_reset_token", sa.Column("used", sa.Boolean(), nullable=True))

    uniques = {u["name"] for u in insp.get_unique_constraints("password_reset_token")}
    if "uq_password_reset_token_token" not in uniques:
        op.create_unique_constraint(
            "uq_password_reset_token_token",
            "password_reset_token",
            ["token"],
        )

    fks = insp.get_foreign_keys("password_reset_token")
    has_fk = any(fk["constrained_columns"] == ["usuario_id"] for fk in fks)
    if not has_fk:
        op.create_foreign_key(
            op.f("fk_password_reset_token_usuario_id_usuario"),
            "password_reset_token",
            "usuario",
            ["usuario_id"],
            ["id"],
        )


def downgrade():
    # O downgrade continua simples: remove a tabela se existir
    bind = op.get_bind()
    insp = inspect(bind)
    if "password_reset_token" in insp.get_table_names():
        op.drop_table("password_reset_token")
