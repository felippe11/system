"""add period columns to formulario"""

from alembic import op
import sqlalchemy as sa

revision = "a4e781302f2b"
down_revision = "15b6b890ce1d"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('formularios') as batch_op:
        batch_op.add_column(sa.Column('data_inicio', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('data_fim', sa.DateTime(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('formularios') as batch_op:
        batch_op.drop_column('data_fim')
        batch_op.drop_column('data_inicio')
