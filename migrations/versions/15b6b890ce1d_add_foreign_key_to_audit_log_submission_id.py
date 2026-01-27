"""Add foreign key to audit_log submission_id

Revision ID: 15b6b890ce1d
Revises: c5b96d8436a6
Create Date: 2025-08-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "15b6b890ce1d"
down_revision = "c5b96d8436a6"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("audit_log") or not inspector.has_table("respostas_formulario"):
        return
    op.execute(
        sa.text(
            """
            UPDATE audit_log
            SET submission_id = NULL
            WHERE submission_id IS NOT NULL
              AND submission_id NOT IN (SELECT id FROM respostas_formulario)
            """
        )
    )
    with op.batch_alter_table('audit_log') as batch_op:
        batch_op.create_foreign_key(
            'fk_audit_log_submission_id_respostas_formulario',
            'respostas_formulario',
            ['submission_id'],
            ['id'],
        )

def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("audit_log"):
        return
    with op.batch_alter_table('audit_log') as batch_op:
        batch_op.drop_constraint(
            'fk_audit_log_submission_id_respostas_formulario',
            type_='foreignkey',
        )
