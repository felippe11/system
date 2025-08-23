"""Add permitir_multiplas_respostas to formularios (idempotente)

Revision ID: 31e6ad1c6a4f
Revises: 15b6b890ce1d
Create Date: 2024-05-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "31e6ad1c6a4f"
down_revision = "15b6b890ce1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("formularios")}

    if "permitir_multiplas_respostas" not in cols:
        # cria com default TRUE para preencher os existentes
        with op.batch_alter_table("formularios") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "permitir_multiplas_respostas",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                )
            )
        # remove o default em nível de schema
        with op.batch_alter_table("formularios") as batch_op:
            batch_op.alter_column("permitir_multiplas_respostas", server_default=None)
    # se já existir, no-op


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("formularios")}

    if "permitir_multiplas_respostas" in cols:
        with op.batch_alter_table("formularios") as batch_op:
            batch_op.drop_column("permitir_multiplas_respostas")
