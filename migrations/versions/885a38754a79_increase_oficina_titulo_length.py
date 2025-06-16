"""increase oficina titulo length

Revision ID: 885a38754a79
Revises: 2744d4add4b2
Create Date: 2025-06-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '885a38754a79'
down_revision = '2744d4add4b2'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('oficina') as batch_op:
        batch_op.alter_column('titulo', type_=sa.String(length=255))

def downgrade():
    with op.batch_alter_table('oficina') as batch_op:
        batch_op.alter_column('titulo', type_=sa.String(length=100))
