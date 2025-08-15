"""move review fields to revisao_config

Revision ID: 2b05f62d38d0
Revises: 64f77f3899ea
Create Date: 2024-08-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '2b05f62d38d0'
down_revision = '64f77f3899ea'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column(
        'revisao_config',
        sa.Column('numero_revisores', sa.Integer(), nullable=True, server_default='2')
    )
    op.add_column(
        'revisao_config',
        sa.Column('prazo_revisao', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'revisao_config',
        sa.Column('modelo_blind', sa.String(length=20), nullable=True, server_default='single')
    )
    inspector = inspect(op.get_bind())
    if 'reviewer_application' in inspector.get_table_names():
        with op.batch_alter_table('reviewer_application') as batch_op:
            batch_op.drop_column('numero_revisores')
            batch_op.drop_column('prazo_revisao')
            batch_op.drop_column('modelo_blind')


def downgrade():
    op.drop_column('revisao_config', 'modelo_blind')
    op.drop_column('revisao_config', 'prazo_revisao')
    op.drop_column('revisao_config', 'numero_revisores')
    op.add_column(
        'reviewer_application',
        sa.Column('numero_revisores', sa.Integer(), nullable=True)
    )
    op.add_column(
        'reviewer_application',
        sa.Column('prazo_revisao', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'reviewer_application',
        sa.Column('modelo_blind', sa.String(length=20), nullable=True)
    )
