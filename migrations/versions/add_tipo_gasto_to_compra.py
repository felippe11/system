"""Add tipo_gasto field to Compra model

Revision ID: add_tipo_gasto_to_compra
Revises: 
Create Date: 2025-01-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_tipo_gasto_to_compra'
down_revision = None  # Will be updated to latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Add tipo_gasto column to compra table."""
    # Add the tipo_gasto column with default value 'custeio'
    op.add_column('compra', sa.Column('tipo_gasto', sa.String(length=20), nullable=False, server_default='custeio'))
    
    # Remove the server default after adding the column (optional, keeps the column default in the model)
    op.alter_column('compra', 'tipo_gasto', server_default=None)


def downgrade():
    """Remove tipo_gasto column from compra table."""
    op.drop_column('compra', 'tipo_gasto')