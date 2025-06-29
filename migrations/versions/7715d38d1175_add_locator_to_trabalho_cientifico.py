"""add locator column to TrabalhoCientifico

Revision ID: 7715d38d1175
Revises: fe25f1583d6c
Create Date: 2025-09-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7715d38d1175'
down_revision = 'fe25f1583d6c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('trabalhos_cientificos') as batch_op:
        batch_op.add_column(sa.Column('locator', sa.String(length=36), nullable=True))
        batch_op.create_unique_constraint('uq_trabalhos_cientificos_locator', ['locator'])


def downgrade():
    with op.batch_alter_table('trabalhos_cientificos') as batch_op:
        batch_op.drop_constraint('uq_trabalhos_cientificos_locator', type_='unique')
        batch_op.drop_column('locator')
