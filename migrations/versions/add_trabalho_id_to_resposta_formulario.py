"""Add trabalho_id to RespostaFormulario

Revision ID: add_trabalho_id_resposta
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_trabalho_id_resposta'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add trabalho_id column to respostas_formulario table
    op.add_column('respostas_formulario', sa.Column('trabalho_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_respostas_formulario_trabalho_id',
        'respostas_formulario', 'submission',
        ['trabalho_id'], ['id']
    )
    
    # Make formulario_id and usuario_id nullable
    op.alter_column('respostas_formulario', 'formulario_id', nullable=True)
    op.alter_column('respostas_formulario', 'usuario_id', nullable=True)


def downgrade():
    # Remove foreign key constraint
    op.drop_constraint('fk_respostas_formulario_trabalho_id', 'respostas_formulario', type_='foreignkey')
    
    # Remove trabalho_id column
    op.drop_column('respostas_formulario', 'trabalho_id')
    
    # Make formulario_id and usuario_id not nullable again
    op.alter_column('respostas_formulario', 'formulario_id', nullable=False)
    op.alter_column('respostas_formulario', 'usuario_id', nullable=False)