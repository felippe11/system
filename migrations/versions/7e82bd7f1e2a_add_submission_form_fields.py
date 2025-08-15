"""add submission form fields

Revision ID: 7e82bd7f1e2a
Revises: 64f77f3899ea
Create Date: 2025-08-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7e82bd7f1e2a'
down_revision = '64f77f3899ea'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'formularios',
        sa.Column('is_submission_form', sa.Boolean(), nullable=False,
                  server_default=sa.false()),
    )
    op.add_column(
        'configuracao_cliente',
        sa.Column('formulario_submissao_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        None,
        'configuracao_cliente',
        'formularios',
        ['formulario_submissao_id'],
        ['id'],
    )


def downgrade():
    op.drop_constraint(
        None, 'configuracao_cliente', type_='foreignkey'
    )
    op.drop_column('configuracao_cliente', 'formulario_submissao_id')
    op.drop_column('formularios', 'is_submission_form')
