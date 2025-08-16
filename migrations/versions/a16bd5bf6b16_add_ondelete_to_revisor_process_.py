"""Add ondelete to revisor_process formulario

Revision ID: a16bd5bf6b16
Revises: 25eb3573df18
Create Date: 2025-08-16 03:00:16.552968

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a16bd5bf6b16'
down_revision = '25eb3573df18'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "fk_revisor_process_formulario_id_formularios",
        "revisor_process",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_revisor_process_formulario_id_formularios"),
        "revisor_process",
        "formularios",
        ["formulario_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        op.f("fk_revisor_process_formulario_id_formularios"),
        "revisor_process",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_revisor_process_formulario_id_formularios",
        "revisor_process",
        "formularios",
        ["formulario_id"],
        ["id"],
    )
