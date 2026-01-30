"""Fix assignment foreign keys

Revision ID: fix_assignment_foreign_keys
Revises: add_assignment_extensions_and_distribution_log
Create Date: 2025-01-02 16:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'fix_assignment_foreign_keys'
down_revision = 'add_assignment_extensions'
branch_labels = None
depends_on = None

def _constraint_exists(bind, constraint_name: str) -> bool:
    """Check if a constraint exists in the database."""
    try:
        result = bind.execute(text("""
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = :constraint_name
        """), {'constraint_name': constraint_name})
        return result.fetchone() is not None
    except Exception:
        return False

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    """Remove incorrect foreign key constraint that references submission table."""
    bind = op.get_bind()
    
    # Drop the incorrect foreign key constraint if it exists
    if _constraint_exists(bind, 'fk_assignment_submission_id_submission'):
        op.drop_constraint('fk_assignment_submission_id_submission', 'assignment', type_='foreignkey')
        print("Removed incorrect foreign key constraint: fk_assignment_submission_id_submission")
    
    # Ensure the correct foreign key exists (it should already exist)
    if not _constraint_exists(bind, 'assignment_resposta_formulario_id_fkey'):
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("assignment")}
        if "assignment_resposta_formulario_id_fkey" not in existing_fks:
            op.create_foreign_key(
                'assignment_resposta_formulario_id_fkey',
                'assignment', 'respostas_formulario',
                ['resposta_formulario_id'], ['id'],
                ondelete='CASCADE'
            )
        print("Created correct foreign key constraint: assignment_resposta_formulario_id_fkey")

def downgrade():
    """Restore the incorrect foreign key (not recommended)."""
    # We don't want to restore the incorrect constraint
    pass