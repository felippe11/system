"""Add cascade to audit_log submission foreign key

Revision ID: d9126a645f16
Revises: 15b6b890ce1d
Create Date: 2025-12-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "d9126a645f16"
down_revision = "15b6b890ce1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("audit_log") or not inspector.has_table("respostas_formulario"):
        return
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.drop_constraint(
            "fk_audit_log_submission_id_respostas_formulario",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_audit_log_submission_id_respostas_formulario",
            "respostas_formulario",
            ["submission_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("audit_log") or not inspector.has_table("respostas_formulario"):
        return
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.drop_constraint(
            "fk_audit_log_submission_id_respostas_formulario",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_audit_log_submission_id_respostas_formulario",
            "respostas_formulario",
            ["submission_id"],
            ["id"],
        )
