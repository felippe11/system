"""add_campos_necessidade_especial_aluno_visitante

Revision ID: 8f6607a2b741
Revises: d4889a23ebd8
Create Date: 2025-08-29 12:10:43.180918

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f6607a2b741'
down_revision = 'd4889a23ebd8'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Add tipo_necessidade_especial and descricao_necessidade_especial columns to aluno_visitante table
    existing_cols = {col['name'] for col in inspector.get_columns("aluno_visitante")}
    if "tipo_necessidade_especial" not in existing_cols:
        op.add_column('aluno_visitante', sa.Column('tipo_necessidade_especial', sa.String(100), nullable=True))
    existing_cols = {col['name'] for col in inspector.get_columns("aluno_visitante")}
    if "descricao_necessidade_especial" not in existing_cols:
        op.add_column('aluno_visitante', sa.Column('descricao_necessidade_especial', sa.Text(), nullable=True))


def downgrade():
    # Remove tipo_necessidade_especial and descricao_necessidade_especial columns from aluno_visitante table
    op.drop_column('aluno_visitante', 'descricao_necessidade_especial')
    op.drop_column('aluno_visitante', 'tipo_necessidade_especial')
