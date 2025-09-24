"""Add BI tables

Revision ID: add_bi_tables
Revises: add_atividade_multipla_data_tables
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_bi_tables'
down_revision = 'add_atividade_multipla_data_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabela relatorio_bi
    op.create_table('relatorio_bi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('tipo_relatorio', sa.String(length=50), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('usuario_criador_id', sa.Integer(), nullable=False),
        sa.Column('filtros_aplicados', sa.Text(), nullable=True),
        sa.Column('periodo_inicio', sa.Date(), nullable=True),
        sa.Column('periodo_fim', sa.Date(), nullable=True),
        sa.Column('dados_relatorio', sa.Text(), nullable=True),
        sa.Column('metricas_calculadas', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('data_criacao', sa.DateTime(), nullable=True),
        sa.Column('data_atualizacao', sa.DateTime(), nullable=True),
        sa.Column('ultima_execucao', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], ),
        sa.ForeignKeyConstraint(['usuario_criador_id'], ['usuario.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar tabela metrica_bi
    op.create_table('metrica_bi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('categoria', sa.String(length=50), nullable=False),
        sa.Column('tipo_metrica', sa.String(length=30), nullable=False),
        sa.Column('formula', sa.Text(), nullable=True),
        sa.Column('cor', sa.String(length=7), nullable=True),
        sa.Column('icone', sa.String(length=50), nullable=True),
        sa.Column('unidade', sa.String(length=20), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.Column('data_criacao', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar tabela dashboard_bi
    op.create_table('dashboard_bi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('usuario_criador_id', sa.Integer(), nullable=False),
        sa.Column('layout_config', sa.Text(), nullable=True),
        sa.Column('widgets_config', sa.Text(), nullable=True),
        sa.Column('filtros_padrao', sa.Text(), nullable=True),
        sa.Column('publico', sa.Boolean(), nullable=True),
        sa.Column('usuarios_permitidos', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.Column('data_criacao', sa.DateTime(), nullable=True),
        sa.Column('data_atualizacao', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], ),
        sa.ForeignKeyConstraint(['usuario_criador_id'], ['usuario.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar tabela widget_bi
    op.create_table('widget_bi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('tipo_widget', sa.String(length=50), nullable=False),
        sa.Column('configuracao', sa.Text(), nullable=True),
        sa.Column('query_sql', sa.Text(), nullable=True),
        sa.Column('metrica_id', sa.Integer(), nullable=True),
        sa.Column('largura', sa.Integer(), nullable=True),
        sa.Column('altura', sa.Integer(), nullable=True),
        sa.Column('posicao_x', sa.Integer(), nullable=True),
        sa.Column('posicao_y', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.Column('data_criacao', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['metrica_id'], ['metrica_bi.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar tabela exportacao_relatorio
    op.create_table('exportacao_relatorio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('relatorio_id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('formato', sa.String(length=10), nullable=False),
        sa.Column('filtros_aplicados', sa.Text(), nullable=True),
        sa.Column('configuracao_export', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('arquivo_path', sa.String(length=500), nullable=True),
        sa.Column('tamanho_arquivo', sa.Integer(), nullable=True),
        sa.Column('mensagem_erro', sa.Text(), nullable=True),
        sa.Column('data_inicio', sa.DateTime(), nullable=True),
        sa.Column('data_conclusao', sa.DateTime(), nullable=True),
        sa.Column('tempo_processamento', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['relatorio_id'], ['relatorio_bi.id'], ),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar tabela cache_relatorio
    op.create_table('cache_relatorio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chave_cache', sa.String(length=255), nullable=False),
        sa.Column('dados_cache', sa.Text(), nullable=False),
        sa.Column('tipo_dados', sa.String(length=50), nullable=False),
        sa.Column('filtros_hash', sa.String(length=64), nullable=False),
        sa.Column('data_criacao', sa.DateTime(), nullable=True),
        sa.Column('data_expiracao', sa.DateTime(), nullable=False),
        sa.Column('hits', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chave_cache')
    )
    
    # Criar tabela alertas_bi
    op.create_table('alertas_bi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('tipo_alerta', sa.String(length=50), nullable=False),
        sa.Column('metrica_id', sa.Integer(), nullable=False),
        sa.Column('condicao', sa.String(length=20), nullable=False),
        sa.Column('valor_limite', sa.Float(), nullable=False),
        sa.Column('periodo_verificacao', sa.Integer(), nullable=True),
        sa.Column('usuarios_notificar', sa.Text(), nullable=True),
        sa.Column('canais_notificacao', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.Column('ultima_verificacao', sa.DateTime(), nullable=True),
        sa.Column('ultimo_disparo', sa.DateTime(), nullable=True),
        sa.Column('data_criacao', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['metrica_id'], ['metrica_bi.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar índices para performance
    op.create_index('ix_relatorio_bi_cliente_id', 'relatorio_bi', ['cliente_id'])
    op.create_index('ix_relatorio_bi_tipo_relatorio', 'relatorio_bi', ['tipo_relatorio'])
    op.create_index('ix_relatorio_bi_status', 'relatorio_bi', ['status'])
    op.create_index('ix_relatorio_bi_data_criacao', 'relatorio_bi', ['data_criacao'])
    
    op.create_index('ix_metrica_bi_categoria', 'metrica_bi', ['categoria'])
    op.create_index('ix_metrica_bi_ativo', 'metrica_bi', ['ativo'])
    
    op.create_index('ix_dashboard_bi_cliente_id', 'dashboard_bi', ['cliente_id'])
    op.create_index('ix_dashboard_bi_ativo', 'dashboard_bi', ['ativo'])
    
    op.create_index('ix_widget_bi_tipo_widget', 'widget_bi', ['tipo_widget'])
    op.create_index('ix_widget_bi_ativo', 'widget_bi', ['ativo'])
    
    op.create_index('ix_exportacao_relatorio_relatorio_id', 'exportacao_relatorio', ['relatorio_id'])
    op.create_index('ix_exportacao_relatorio_status', 'exportacao_relatorio', ['status'])
    op.create_index('ix_exportacao_relatorio_data_inicio', 'exportacao_relatorio', ['data_inicio'])
    
    op.create_index('ix_cache_relatorio_chave_cache', 'cache_relatorio', ['chave_cache'])
    op.create_index('ix_cache_relatorio_tipo_dados', 'cache_relatorio', ['tipo_dados'])
    op.create_index('ix_cache_relatorio_data_expiracao', 'cache_relatorio', ['data_expiracao'])
    
    op.create_index('ix_alertas_bi_metrica_id', 'alertas_bi', ['metrica_id'])
    op.create_index('ix_alertas_bi_ativo', 'alertas_bi', ['ativo'])
    op.create_index('ix_alertas_bi_tipo_alerta', 'alertas_bi', ['tipo_alerta'])


def downgrade():
    # Remover índices
    op.drop_index('ix_alertas_bi_tipo_alerta', table_name='alertas_bi')
    op.drop_index('ix_alertas_bi_ativo', table_name='alertas_bi')
    op.drop_index('ix_alertas_bi_metrica_id', table_name='alertas_bi')
    
    op.drop_index('ix_cache_relatorio_data_expiracao', table_name='cache_relatorio')
    op.drop_index('ix_cache_relatorio_tipo_dados', table_name='cache_relatorio')
    op.drop_index('ix_cache_relatorio_chave_cache', table_name='cache_relatorio')
    
    op.drop_index('ix_exportacao_relatorio_data_inicio', table_name='exportacao_relatorio')
    op.drop_index('ix_exportacao_relatorio_status', table_name='exportacao_relatorio')
    op.drop_index('ix_exportacao_relatorio_relatorio_id', table_name='exportacao_relatorio')
    
    op.drop_index('ix_widget_bi_ativo', table_name='widget_bi')
    op.drop_index('ix_widget_bi_tipo_widget', table_name='widget_bi')
    
    op.drop_index('ix_dashboard_bi_ativo', table_name='dashboard_bi')
    op.drop_index('ix_dashboard_bi_cliente_id', table_name='dashboard_bi')
    
    op.drop_index('ix_metrica_bi_ativo', table_name='metrica_bi')
    op.drop_index('ix_metrica_bi_categoria', table_name='metrica_bi')
    
    op.drop_index('ix_relatorio_bi_data_criacao', table_name='relatorio_bi')
    op.drop_index('ix_relatorio_bi_status', table_name='relatorio_bi')
    op.drop_index('ix_relatorio_bi_tipo_relatorio', table_name='relatorio_bi')
    op.drop_index('ix_relatorio_bi_cliente_id', table_name='relatorio_bi')
    
    # Remover tabelas
    op.drop_table('alertas_bi')
    op.drop_table('cache_relatorio')
    op.drop_table('exportacao_relatorio')
    op.drop_table('widget_bi')
    op.drop_table('dashboard_bi')
    op.drop_table('metrica_bi')
    op.drop_table('relatorio_bi')
