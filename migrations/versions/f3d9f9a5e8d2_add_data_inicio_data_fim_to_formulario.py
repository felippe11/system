"""add data_inicio and data_fim to formulario

Revision ID: f3d9f9a5e8d2
Revises: 15b6b890ce1d
Create Date: 2024-08-11 20:38:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f3d9f9a5e8d2"
down_revision = "15b6b890ce1d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("formularios", sa.Column("data_inicio", sa.DateTime(), nullable=True))
    op.add_column("formularios", sa.Column("data_fim", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("formularios", "data_inicio")
    op.drop_column("formularios", "data_fim")
