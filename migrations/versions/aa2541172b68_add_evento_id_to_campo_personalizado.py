"""add evento_id to CampoPersonalizadoCadastro

Revision ID: aa2541172b68
Revises: 2273dba1d6d7
Create Date: 2025-10-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'aa2541172b68'
down_revision = '2273dba1d6d7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('campos_personalizados_cadastro') as batch_op:
        batch_op.add_column(sa.Column('evento_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_campo_evento', 'evento', ['evento_id'], ['id'])


def downgrade():
    with op.batch_alter_table('campos_personalizados_cadastro') as batch_op:
        batch_op.drop_constraint('fk_campo_evento', type_='foreignkey')
        batch_op.drop_column('evento_id')
