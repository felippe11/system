"""add fechado to horario_visitacao

Revision ID: f592acec47c1
Revises: e89dc0a9d598, c0f0b9fa83c0, 085998713db1
Create Date: 2025-02-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f592acec47c1'
down_revision = ('e89dc0a9d598', 'c0f0b9fa83c0', '085998713db1')
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('horario_visitacao', sa.Column('fechado', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column('horario_visitacao', 'fechado')
