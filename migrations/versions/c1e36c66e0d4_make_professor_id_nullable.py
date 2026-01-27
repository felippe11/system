"""make professor_id nullable in agendamento_visita

Revision ID: c1e36c66e0d4
Revises: f3c52d6c9b16
Create Date: 2025-08-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "c1e36c66e0d4"
down_revision = "f3c52d6c9b16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("agendamento_visita"):
        return
    with op.batch_alter_table("agendamento_visita") as batch_op:
        batch_op.alter_column("professor_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("agendamento_visita"):
        return
    with op.batch_alter_table("agendamento_visita") as batch_op:
        batch_op.alter_column("professor_id", existing_type=sa.Integer(), nullable=False)
