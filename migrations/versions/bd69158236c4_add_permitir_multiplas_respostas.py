"""add permitir_multiplas_respostas field to formulario

Revision ID: bd69158236c4
Revises: 15b6b890ce1d
Create Date: 2025-02-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "bd69158236c4"
down_revision = "15b6b890ce1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("formularios"):
        return
    with op.batch_alter_table("formularios") as batch_op:
        batch_op.add_column(
            sa.Column("permitir_multiplas_respostas", sa.Boolean(), nullable=True, server_default=sa.true())
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("formularios"):
        return
    with op.batch_alter_table("formularios") as batch_op:
        batch_op.drop_column("permitir_multiplas_respostas")
