"""add cascade to password_reset_token.usuario_id

Revision ID: c5b96d8436a6
Revises: e4cb3d4630b1
Create Date: 2025-12-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c5b96d8436a6"
down_revision = "e6154b1f9b2a"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("password_reset_token"):
        return
    op.drop_constraint(
        "fk_password_reset_token_usuario_id_usuario",
        "password_reset_token",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_password_reset_token_usuario_id_usuario"),
        "password_reset_token",
        "usuario",
        ["usuario_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("password_reset_token"):
        return
    op.drop_constraint(
        op.f("fk_password_reset_token_usuario_id_usuario"),
        "password_reset_token",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_password_reset_token_usuario_id_usuario",
        "password_reset_token",
        "usuario",
        ["usuario_id"],
        ["id"],
    )
