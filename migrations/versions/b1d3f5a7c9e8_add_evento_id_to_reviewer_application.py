"""add evento_id to reviewer application

Revision ID: b1d3f5a7c9e8
Revises: 91da4eee8c01
Create Date: 2025-07-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1d3f5a7c9e8'
down_revision = '91da4eee8c01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('reviewer_application', sa.Column('evento_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_reviewer_application_evento_id_evento', 'reviewer_application', 'evento', ['evento_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_reviewer_application_evento_id_evento', 'reviewer_application', type_='foreignkey')
    op.drop_column('reviewer_application', 'evento_id')
