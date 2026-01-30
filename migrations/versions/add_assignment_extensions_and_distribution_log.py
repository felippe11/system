"""Add assignment extensions and distribution log table

Revision ID: add_assignment_extensions
Revises: f0c6022a4f5a
Create Date: 2025-01-22 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_assignment_extensions"
down_revision = "f0c6022a4f5a"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Add new columns to assignment table
    existing_cols = {col['name'] for col in inspector.get_columns("assignment")}
    if "distribution_type" not in existing_cols:
        op.add_column('assignment', sa.Column('distribution_type', sa.String(20), nullable=True))
    existing_cols = {col['name'] for col in inspector.get_columns("assignment")}
    if "distribution_date" not in existing_cols:
        op.add_column('assignment', sa.Column('distribution_date', sa.DateTime, nullable=True))
    existing_cols = {col['name'] for col in inspector.get_columns("assignment")}
    if "distributed_by" not in existing_cols:
        op.add_column('assignment', sa.Column('distributed_by', sa.Integer, nullable=True))
    existing_cols = {col['name'] for col in inspector.get_columns("assignment")}
    if "notes" not in existing_cols:
        op.add_column('assignment', sa.Column('notes', sa.Text, nullable=True))
    
    # Add foreign key constraint for distributed_by
    existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("assignment")}
    if "fk_assignment_distributed_by" not in existing_fks:
        op.create_foreign_key(
            'fk_assignment_distributed_by',
            'assignment', 'usuario',
            ['distributed_by'], ['id'],
            ondelete='SET NULL'
        )
    
    # Create distribution_log table
    if not inspector.has_table("distribution_log"):
        op.create_table(
            'distribution_log',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('evento_id', sa.Integer, nullable=False),
            sa.Column('distribution_type', sa.String(20), nullable=False),
            sa.Column('total_works', sa.Integer, nullable=False),
            sa.Column('total_reviewers', sa.Integer, nullable=False),
            sa.Column('assignments_created', sa.Integer, nullable=False),
            sa.Column('distribution_date', sa.DateTime, nullable=False),
            sa.Column('distributed_by', sa.Integer, nullable=False),
            sa.Column('filters_applied', sa.JSON, nullable=True),
            sa.Column('notes', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
        )
    
    # Add foreign key constraints for distribution_log
    if inspector.has_table("distribution_log"):
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("distribution_log")}
        if "fk_distribution_log_evento" not in existing_fks:
            op.create_foreign_key(
                'fk_distribution_log_evento',
                'distribution_log', 'evento',
                ['evento_id'], ['id'],
                ondelete='CASCADE'
            )
        
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("distribution_log")}
        if "fk_distribution_log_distributed_by" not in existing_fks:
            op.create_foreign_key(
                'fk_distribution_log_distributed_by',
                'distribution_log', 'usuario',
                ['distributed_by'], ['id'],
                ondelete='CASCADE'
            )
    
    # Create indexes for better performance
    op.create_index('idx_assignment_distribution_type', 'assignment', ['distribution_type'])
    op.create_index('idx_assignment_distribution_date', 'assignment', ['distribution_date'])
    if inspector.has_table("distribution_log"):
        op.create_index('idx_distribution_log_evento', 'distribution_log', ['evento_id'])
        op.create_index('idx_distribution_log_date', 'distribution_log', ['distribution_date'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_distribution_log_date')
    op.drop_index('idx_distribution_log_evento')
    op.drop_index('idx_assignment_distribution_date')
    op.drop_index('idx_assignment_distribution_type')
    
    # Drop distribution_log table
    op.drop_table('distribution_log')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_assignment_distributed_by', 'assignment', type_='foreignkey')
    
    # Drop columns from assignment table
    op.drop_column('assignment', 'notes')
    op.drop_column('assignment', 'distributed_by')
    op.drop_column('assignment', 'distribution_date')
    op.drop_column('assignment', 'distribution_type')
