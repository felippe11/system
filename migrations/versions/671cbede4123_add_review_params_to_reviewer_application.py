"""add review control fields to reviewer_application

Revision ID: 671cbede4123
Revises: b1d3f5a7c9e8
Create Date: 2026-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '671cbede4123'
down_revision = 'b1d3f5a7c9e8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('reviewer_application') as batch_op:
        batch_op.add_column(sa.Column('numero_revisores', sa.Integer(), nullable=False, server_default='2'))
        batch_op.add_column(sa.Column('prazo_revisao', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('modelo_blind', sa.String(length=20), nullable=False, server_default='single'))


def downgrade() -> None:
    with op.batch_alter_table('reviewer_application') as batch_op:
        batch_op.drop_column('modelo_blind')
        batch_op.drop_column('prazo_revisao')
        batch_op.drop_column('numero_revisores')
