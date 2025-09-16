"""Fix MaterialDisponivel table columns to match model

Revision ID: fix_material_disponivel_columns
Revises: d8e9f1a2b3c4
Create Date: 2025-01-28 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_material_disponivel_columns'
down_revision = 'd8e9f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade():
    # Check current table structure first
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('material_disponivel')]
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('material_disponivel')]
    existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('material_disponivel')]
    
    # Add missing columns to material_disponivel table
    if 'nome' not in existing_columns:
        op.add_column('material_disponivel', sa.Column('nome', sa.String(255), nullable=False, server_default='Material'))
    if 'descricao' not in existing_columns:
        op.add_column('material_disponivel', sa.Column('descricao', sa.Text(), nullable=True))
    if 'tipo_material' not in existing_columns:
        op.add_column('material_disponivel', sa.Column('tipo_material', sa.String(100), nullable=False, server_default='consumivel'))
    if 'unidade_medida' not in existing_columns:
        op.add_column('material_disponivel', sa.Column('unidade_medida', sa.String(50), nullable=False, server_default='unidade'))
    if 'quantidade_minima_pedido' not in existing_columns:
        op.add_column('material_disponivel', sa.Column('quantidade_minima_pedido', sa.Integer(), nullable=False, server_default='1'))
    if 'quantidade_maxima_pedido' not in existing_columns:
        op.add_column('material_disponivel', sa.Column('quantidade_maxima_pedido', sa.Integer(), nullable=False, server_default='100'))
    if 'disponivel_para_solicitacao' not in existing_columns:
        op.add_column('material_disponivel', sa.Column('disponivel_para_solicitacao', sa.Boolean(), nullable=False, server_default='true'))
    if 'quantidade_estoque' not in existing_columns:
        op.add_column('material_disponivel', sa.Column('quantidade_estoque', sa.Integer(), nullable=False, server_default='0'))
    if 'estoque_minimo' not in existing_columns:
        op.add_column('material_disponivel', sa.Column('estoque_minimo', sa.Integer(), nullable=False, server_default='0'))
    
    # Remove old columns that don't match the model (only if they exist)
    if 'material_disponivel_material_id_fkey' in existing_fks:
        op.drop_constraint('material_disponivel_material_id_fkey', 'material_disponivel', type_='foreignkey')
    if 'ix_material_disponivel_material_id' in existing_indexes:
        op.drop_index('ix_material_disponivel_material_id', 'material_disponivel')
    if 'material_id' in existing_columns:
        op.drop_column('material_disponivel', 'material_id')
    if 'quantidade_minima' in existing_columns:
        op.drop_column('material_disponivel', 'quantidade_minima')
    if 'quantidade_maxima' in existing_columns:
        op.drop_column('material_disponivel', 'quantidade_maxima')
    if 'controle_estoque' in existing_columns:
        op.drop_column('material_disponivel', 'controle_estoque')
    
    # Remove the server_default from columns after adding them
    if 'nome' in existing_columns or 'nome' not in existing_columns:
        op.alter_column('material_disponivel', 'nome', server_default=None)
    if 'tipo_material' in existing_columns or 'tipo_material' not in existing_columns:
        op.alter_column('material_disponivel', 'tipo_material', server_default=None)
    if 'unidade_medida' in existing_columns or 'unidade_medida' not in existing_columns:
        op.alter_column('material_disponivel', 'unidade_medida', server_default=None)
    if 'quantidade_minima_pedido' in existing_columns or 'quantidade_minima_pedido' not in existing_columns:
        op.alter_column('material_disponivel', 'quantidade_minima_pedido', server_default=None)
    if 'quantidade_maxima_pedido' in existing_columns or 'quantidade_maxima_pedido' not in existing_columns:
        op.alter_column('material_disponivel', 'quantidade_maxima_pedido', server_default=None)
    if 'disponivel_para_solicitacao' in existing_columns or 'disponivel_para_solicitacao' not in existing_columns:
        op.alter_column('material_disponivel', 'disponivel_para_solicitacao', server_default=None)
    if 'quantidade_estoque' in existing_columns or 'quantidade_estoque' not in existing_columns:
        op.alter_column('material_disponivel', 'quantidade_estoque', server_default=None)
    if 'estoque_minimo' in existing_columns or 'estoque_minimo' not in existing_columns:
        op.alter_column('material_disponivel', 'estoque_minimo', server_default=None)


def downgrade():
    # Reverse the changes
    op.add_column('material_disponivel', sa.Column('material_id', sa.Integer(), nullable=False))
    op.add_column('material_disponivel', sa.Column('quantidade_minima', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('material_disponivel', sa.Column('quantidade_maxima', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('material_disponivel', sa.Column('controle_estoque', sa.Boolean(), nullable=False, server_default='true'))
    
    op.create_foreign_key('material_disponivel_material_id_fkey', 'material_disponivel', 'material', ['material_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_material_disponivel_material_id', 'material_disponivel', ['material_id'])
    
    # Remove the new columns
    op.drop_column('material_disponivel', 'estoque_minimo')
    op.drop_column('material_disponivel', 'quantidade_estoque')
    op.drop_column('material_disponivel', 'disponivel_para_solicitacao')
    op.drop_column('material_disponivel', 'quantidade_maxima_pedido')
    op.drop_column('material_disponivel', 'quantidade_minima_pedido')
    op.drop_column('material_disponivel', 'unidade_medida')
    op.drop_column('material_disponivel', 'tipo_material')
    op.drop_column('material_disponivel', 'descricao')
    op.drop_column('material_disponivel', 'nome')