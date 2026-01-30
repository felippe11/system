"""Add trabalho_id to RespostaFormulario

Revision ID: add_trabalho_id_resposta
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_trabalho_id_resposta'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {
        col["name"] for col in inspector.get_columns("respostas_formulario")
    }

    if "trabalho_id" not in existing_cols:
        op.add_column(
            "respostas_formulario",
            sa.Column("trabalho_id", sa.Integer(), nullable=True),
        )

    existing_fks = {
        fk["name"] for fk in inspector.get_foreign_keys("respostas_formulario")
    }
    if "fk_respostas_formulario_trabalho_id" not in existing_fks:
        op.create_foreign_key(
            "fk_respostas_formulario_trabalho_id",
            "respostas_formulario",
            "submission",
            ["trabalho_id"],
            ["id"],
        )

    if "formulario_id" in existing_cols:
        op.alter_column("respostas_formulario", "formulario_id", nullable=True)
    if "usuario_id" in existing_cols:
        op.alter_column("respostas_formulario", "usuario_id", nullable=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {
        col["name"] for col in inspector.get_columns("respostas_formulario")
    }
    existing_fks = {
        fk["name"] for fk in inspector.get_foreign_keys("respostas_formulario")
    }

    if "fk_respostas_formulario_trabalho_id" in existing_fks:
        op.drop_constraint(
            "fk_respostas_formulario_trabalho_id",
            "respostas_formulario",
            type_="foreignkey",
        )

    if "trabalho_id" in existing_cols:
        op.drop_column("respostas_formulario", "trabalho_id")

    if "formulario_id" in existing_cols:
        op.alter_column("respostas_formulario", "formulario_id", nullable=False)
    if "usuario_id" in existing_cols:
        op.alter_column("respostas_formulario", "usuario_id", nullable=False)
