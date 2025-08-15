"""add permitir_multiplas_respostas to formularios

Revision ID: 8b761cbdc50d
Revises: 15b6b890ce1d
Create Date: 2024-06-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "8b761cbdc50d"
down_revision = "15b6b890ce1d"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('formularios') as batch_op:
        batch_op.add_column(sa.Column('permitir_multiplas_respostas', sa.Boolean(), nullable=True, server_default=sa.true()))
    op.execute(sa.text('UPDATE formularios SET permitir_multiplas_respostas = TRUE'))
    with op.batch_alter_table('formularios') as batch_op:
        batch_op.alter_column('permitir_multiplas_respostas', server_default=None)

def downgrade() -> None:
    with op.batch_alter_table('formularios') as batch_op:
        batch_op.drop_column('permitir_multiplas_respostas')
