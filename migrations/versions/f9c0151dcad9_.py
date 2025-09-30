"""empty message

Revision ID: f9c0151dcad9
Revises: add_assinatura_certificado_revisor
Create Date: 2025-09-29 20:31:03.438871
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f9c0151dcad9'
down_revision = 'add_assinatura_certificado_revisor'
branch_labels = None
depends_on = None


def upgrade():
    # Esta migração não precisa fazer nada: a coluna já foi criada na anterior
    pass


def downgrade():
    # Também não precisa reverter nada aqui
    pass
