"""add fields to work_metadata

Revision ID: 79c3c0f95577
Revises: b7f45c8e9d1a
Create Date: 2025-02-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '79c3c0f95577'
down_revision = 'b7f45c8e9d1a'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('work_metadata', sa.Column('titulo', sa.String(length=255), nullable=True))
    op.add_column('work_metadata', sa.Column('categoria', sa.String(length=100), nullable=True))
    op.add_column('work_metadata', sa.Column('rede_ensino', sa.String(length=100), nullable=True))
    op.add_column('work_metadata', sa.Column('etapa_ensino', sa.String(length=100), nullable=True))
    op.add_column('work_metadata', sa.Column('pdf_url', sa.String(length=255), nullable=True))
    op.add_column('work_metadata', sa.Column('evento_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_work_metadata_evento', 'work_metadata', 'evento', ['evento_id'], ['id']
    )


def downgrade():
    op.drop_constraint('fk_work_metadata_evento', 'work_metadata', type_='foreignkey')
    op.drop_column('work_metadata', 'evento_id')
    op.drop_column('work_metadata', 'pdf_url')
    op.drop_column('work_metadata', 'etapa_ensino')
    op.drop_column('work_metadata', 'rede_ensino')
    op.drop_column('work_metadata', 'categoria')
    op.drop_column('work_metadata', 'titulo')
