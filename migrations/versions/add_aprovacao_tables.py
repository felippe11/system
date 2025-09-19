"""Add aprovacao tables

Revision ID: add_aprovacao_tables
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_aprovacao_tables'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Criar tabela nivel_aprovacao
    op.create_table('nivel_aprovacao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('valor_minimo', sa.Float(), nullable=False, default=0.0),
        sa.Column('valor_maximo', sa.Float(), nullable=True),
        sa.Column('obrigatorio', sa.Boolean(), nullable=False, default=True),
        sa.Column('ativo', sa.Boolean(), nullable=False, default=True),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar tabela aprovacao_compra
    op.create_table('aprovacao_compra',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='pendente'),
        sa.Column('comentario', sa.Text(), nullable=True),
        sa.Column('data_aprovacao', sa.DateTime(), nullable=True),
        sa.Column('compra_id', sa.Integer(), nullable=False),
        sa.Column('nivel_aprovacao_id', sa.Integer(), nullable=False),
        sa.Column('aprovador_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['aprovador_id'], ['usuario.id'], ),
        sa.ForeignKeyConstraint(['compra_id'], ['compra.id'], ),
        sa.ForeignKeyConstraint(['nivel_aprovacao_id'], ['nivel_aprovacao.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('aprovacao_compra')
    op.drop_table('nivel_aprovacao')