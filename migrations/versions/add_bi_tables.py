"""Add BI tables

Revision ID: add_bi_tables
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_bi_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create relatorio_bi table
    op.create_table('relatorio_bi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('tipo_relatorio', sa.String(length=50), nullable=False),
        sa.Column('filtros_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create metrica_bi table
    op.create_table('metrica_bi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('formula_sql', sa.Text(), nullable=True),
        sa.Column('tipo_dado', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    
    # Create dashboard_bi table
    op.create_table('dashboard_bi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('layout_json', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('refresh_interval', sa.Integer(), nullable=True),
        sa.Column('theme', sa.String(length=20), nullable=True),
        sa.Column('filtros_padrao', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create widget_bi table
    op.create_table('widget_bi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dashboard_id', sa.Integer(), nullable=False),
        sa.Column('metrica_id', sa.Integer(), nullable=True),
        sa.Column('titulo', sa.String(length=255), nullable=False),
        sa.Column('tipo_visualizacao', sa.String(length=50), nullable=False),
        sa.Column('config_json', sa.Text(), nullable=True),
        sa.Column('posicao_x', sa.Integer(), nullable=True),
        sa.Column('posicao_y', sa.Integer(), nullable=True),
        sa.Column('largura', sa.Integer(), nullable=True),
        sa.Column('altura', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dashboard_id'], ['dashboard_bi.id'], ),
        sa.ForeignKeyConstraint(['metrica_id'], ['metrica_bi.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create exportacao_relatorio table
    op.create_table('exportacao_relatorio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('relatorio_id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('formato', sa.String(length=10), nullable=False),
        sa.Column('caminho_arquivo', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('data_solicitacao', sa.DateTime(), nullable=True),
        sa.Column('data_conclusao', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['relatorio_id'], ['relatorio_bi.id'], ),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create cache_relatorio table
    op.create_table('cache_relatorio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chave_cache', sa.String(length=255), nullable=False),
        sa.Column('dados_json', sa.Text(), nullable=False),
        sa.Column('data_expiracao', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chave_cache')
    )
    
    # Create alertas_bi table
    op.create_table('alertas_bi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('metrica_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('condicao', sa.String(length=255), nullable=False),
        sa.Column('frequencia', sa.String(length=50), nullable=False),
        sa.Column('canais_notificacao', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.Column('last_triggered', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], ),
        sa.ForeignKeyConstraint(['metrica_id'], ['metrica_bi.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('alertas_bi')
    op.drop_table('cache_relatorio')
    op.drop_table('exportacao_relatorio')
    op.drop_table('widget_bi')
    op.drop_table('dashboard_bi')
    op.drop_table('metrica_bi')
    op.drop_table('relatorio_bi')