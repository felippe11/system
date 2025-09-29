"""merge heads: assinatura + 3468165c5bd2

Revision ID: 1334695f7e0a
Revises: 3468165c5bd2, add_assinatura_certificado_revisor
Create Date: 2025-09-29 20:27:16.082545

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1334695f7e0a'
down_revision = ('3468165c5bd2', 'add_assinatura_certificado_revisor')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
