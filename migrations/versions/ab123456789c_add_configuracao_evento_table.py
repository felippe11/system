"""add configuracao_evento table

Revision ID: ab123456789c
Revises: 2273dba1d6d7
Create Date: 2025-07-09 19:51:16.921200

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'ab123456789c'
down_revision = '2273dba1d6d7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'configuracao_evento' in inspector.get_table_names():
        return
    op.create_table(
        'configuracao_evento',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('evento_id', sa.Integer(), nullable=False),
        sa.Column('permitir_checkin_global', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('habilitar_feedback', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('habilitar_certificado_individual', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('habilitar_qrcode_evento_credenciamento', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('habilitar_submissao_trabalhos', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('mostrar_taxa', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('taxa_diferenciada', sa.Numeric(5, 2), nullable=True),
        sa.Column('allowed_file_types', sa.String(length=100), nullable=True, server_default='pdf'),
        sa.Column('review_model', sa.String(length=20), nullable=True, server_default='single'),
        sa.Column('num_revisores_min', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('num_revisores_max', sa.Integer(), nullable=True, server_default='2'),
        sa.Column('prazo_parecer_dias', sa.Integer(), nullable=True, server_default='14'),
        sa.Column('obrigatorio_nome', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('obrigatorio_cpf', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('obrigatorio_email', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('obrigatorio_senha', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('obrigatorio_formacao', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('limite_eventos', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('limite_inscritos', sa.Integer(), nullable=True, server_default='1000'),
        sa.Column('limite_formularios', sa.Integer(), nullable=True, server_default='3'),
        sa.Column('limite_revisores', sa.Integer(), nullable=True, server_default='2'),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id']),
        sa.ForeignKeyConstraint(['evento_id'], ['evento.id']),
    )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'configuracao_evento' in inspector.get_table_names():
        op.drop_table('configuracao_evento')
