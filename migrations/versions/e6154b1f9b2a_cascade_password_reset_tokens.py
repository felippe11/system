"""Cascade delete password reset tokens

Revision ID: e6154b1f9b2a
Revises: 9bac7f9f0073
Create Date: 2025-08-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e6154b1f9b2a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        "fk_password_reset_token_usuario_id_usuario",
        "password_reset_token",
        "usuario",
        ["usuario_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
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
        "fk_password_reset_token_usuario_id_usuario",
        "password_reset_token",
        "usuario",
        ["usuario_id"],
        ["id"],
    )
