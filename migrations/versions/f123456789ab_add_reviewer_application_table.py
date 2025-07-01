"""add reviewer application table

Revision ID: f123456789ab
Revises: fe25f1583d6c
Create Date: 2025-10-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'f123456789ab'
down_revision = 'fe25f1583d6c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'reviewer_application',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('reviewer_application')
