"""add evento_formulario association

Revision ID: d33e6d59d2e3
Revises: 7d9bf72dc081
Create Date: 2025-07-05 04:08:30.657683

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd33e6d59d2e3'
down_revision = '7d9bf72dc081'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'evento_formulario',
        sa.Column('evento_id', sa.Integer(), sa.ForeignKey('evento.id'), primary_key=True),
        sa.Column('formulario_id', sa.Integer(), sa.ForeignKey('formularios.id'), primary_key=True),
    )


def downgrade():
    op.drop_table('evento_formulario')
