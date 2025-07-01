"""rename revisor process availability fields

Revision ID: abc123456789
Revises: f6c95551a473
Create Date: 2025-07-01 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'abc123456789'
down_revision = 'f6c95551a473'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    cols = [c['name'] for c in sa.inspect(conn).get_columns('revisor_process')]
    with op.batch_alter_table('revisor_process', schema=None) as batch_op:
        if 'inicio_disponibilidade' in cols:
            batch_op.alter_column('inicio_disponibilidade', new_column_name='availability_start')
        if 'fim_disponibilidade' in cols:
            batch_op.alter_column('fim_disponibilidade', new_column_name='availability_end')


def downgrade():
    conn = op.get_bind()
    cols = [c['name'] for c in sa.inspect(conn).get_columns('revisor_process')]
    with op.batch_alter_table('revisor_process', schema=None) as batch_op:
        if 'availability_start' in cols:
            batch_op.alter_column('availability_start', new_column_name='inicio_disponibilidade')
        if 'availability_end' in cols:
            batch_op.alter_column('availability_end', new_column_name='fim_disponibilidade')
