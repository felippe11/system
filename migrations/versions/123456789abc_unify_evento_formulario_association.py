"""unify evento_formulario association

Revision ID: 123456789abc
Revises: ffbc68259c84
Create Date: 2025-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '123456789abc'
down_revision = 'ffbc68259c84'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('evento_formulario')
    op.drop_table('formulario_evento_association')
    op.create_table(
        'evento_formulario_association',
        sa.Column('evento_id', sa.Integer(), sa.ForeignKey('evento.id'), primary_key=True),
        sa.Column('formulario_id', sa.Integer(), sa.ForeignKey('formularios.id'), primary_key=True),
    )


def downgrade():
    op.drop_table('evento_formulario_association')
    op.create_table(
        'formulario_evento_association',
        sa.Column('formulario_id', sa.Integer(), sa.ForeignKey('formularios.id'), primary_key=True),
        sa.Column('evento_id', sa.Integer(), sa.ForeignKey('evento.id'), primary_key=True),
    )
    op.create_table(
        'evento_formulario',
        sa.Column('evento_id', sa.Integer(), sa.ForeignKey('evento.id'), primary_key=True),
        sa.Column('formulario_id', sa.Integer(), sa.ForeignKey('formularios.id'), primary_key=True),
    )
