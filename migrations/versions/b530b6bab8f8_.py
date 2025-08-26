"""empty message

Revision ID: b530b6bab8f8
Revises: d1b3a515bc9e
Create Date: 2025-08-25 14:42:41.790992

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b530b6bab8f8"
down_revision = "d1b3a515bc9e"
branch_labels = None
depends_on = None


def upgrade():
    # Remoção idempotente: não falha se a coluna não existir
    op.execute(
        "ALTER TABLE agendamento_visita DROP COLUMN IF EXISTS precisa_transporte"
    )


def downgrade():
    # Recria a coluna apenas se ela ainda não existir
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'agendamento_visita'
                  AND column_name = 'precisa_transporte'
            ) THEN
                ALTER TABLE agendamento_visita
                ADD COLUMN precisa_transporte boolean;
            END IF;
        END$$;
        """
    )
