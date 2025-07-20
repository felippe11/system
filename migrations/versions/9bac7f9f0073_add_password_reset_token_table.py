"""Add password reset token table

Revision ID: 9bac7f9f0073
Revises: a5154a3f3a4c
Create Date: 2025-07-20 04:08:13

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9bac7f9f0073'
down_revision = 'a5154a3f3a4c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'password_reset_token',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuario.id'), nullable=False),
        sa.Column('token', sa.String(length=36), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True),
    )


def downgrade():
    op.drop_table('password_reset_token')
