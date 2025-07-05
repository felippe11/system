"""add submission_only to EventoInscricaoTipo

Revision ID: c1a2b3d4e5f6
Revises: 7d9bf72dc081
Create Date: 2025-10-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c1a2b3d4e5f6'
down_revision = '7d9bf72dc081'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('evento_inscricao_tipo') as batch_op:
        batch_op.add_column(sa.Column('submission_only', sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('evento_inscricao_tipo') as batch_op:
        batch_op.drop_column('submission_only')
