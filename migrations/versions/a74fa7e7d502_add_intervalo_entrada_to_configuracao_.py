"""add intervalo_entrada to configuracao_agendamento

Revision ID: a74fa7e7d502
Revises: b530b6bab8f8
Create Date: 2025-08-25 15:23:08.552129

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a74fa7e7d502'
down_revision = 'b530b6bab8f8'
branch_labels = None
depends_on = None

TABLE = "configuracao_agendamento"
COL = "intervalo_entrada"

def upgrade():
    # Cria com default e NOT NULL de forma idempotente (Postgres)
    op.execute(f"""
        ALTER TABLE {TABLE}
        ADD COLUMN IF NOT EXISTS {COL} INTEGER NOT NULL DEFAULT 15
    """)
    # Se quiser remover o default após popular (opcional):
    op.execute(f"ALTER TABLE {TABLE} ALTER COLUMN {COL} DROP DEFAULT")

def downgrade():
    op.execute(f"ALTER TABLE {TABLE} DROP COLUMN IF EXISTS {COL}")