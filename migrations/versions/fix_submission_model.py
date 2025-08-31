"""Fix submission model constraints

Revision ID: fix_submission_001
Revises: 
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_submission_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database schema to fix submission model constraints."""
    
    # Primeiro, limpar dados órfãos
    op.execute("""
        DELETE FROM submission 
        WHERE author_id IS NULL OR evento_id IS NULL
    """)
    
    # Tornar author_id obrigatório
    op.alter_column('submission', 'author_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # Tornar evento_id obrigatório
    op.alter_column('submission', 'evento_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # Adicionar constraint para garantir que pelo menos um identificador de revisor existe
    op.execute("""
        ALTER TABLE review 
        ADD CONSTRAINT check_reviewer_identification 
        CHECK (reviewer_id IS NOT NULL OR reviewer_name IS NOT NULL)
    """)
    
    # Adicionar índices para melhor performance
    op.create_index('idx_submission_author_evento', 'submission', ['author_id', 'evento_id'])
    op.create_index('idx_submission_status', 'submission', ['status'])
    op.create_index('idx_review_submission', 'review', ['submission_id'])
    op.create_index('idx_assignment_reviewer', 'assignment', ['reviewer_id'])
    
    # Adicionar constraint para evitar submissões duplicadas do mesmo autor no mesmo evento
    op.create_unique_constraint(
        'uq_submission_author_evento', 
        'submission', 
        ['author_id', 'evento_id']
    )


def downgrade():
    """Downgrade database schema."""
    
    # Remover constraints e índices
    op.drop_constraint('uq_submission_author_evento', 'submission', type_='unique')
    op.drop_index('idx_assignment_reviewer')
    op.drop_index('idx_review_submission')
    op.drop_index('idx_submission_status')
    op.drop_index('idx_submission_author_evento')
    
    op.execute("ALTER TABLE review DROP CONSTRAINT IF EXISTS check_reviewer_identification")
    
    # Reverter campos para nullable
    op.alter_column('submission', 'evento_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    op.alter_column('submission', 'author_id',
                    existing_type=sa.Integer(),
                    nullable=True)