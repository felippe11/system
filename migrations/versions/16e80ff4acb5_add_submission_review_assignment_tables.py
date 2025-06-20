"""add Submission, Review, and Assignment tables"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '16e80ff4acb5'
down_revision = '2bb295ff7424'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'submission',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=255), nullable=True),
        sa.Column('locator', sa.String(length=255), nullable=True),
        sa.Column('code_hash', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('area_id', sa.Integer(), nullable=True),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_table(
        'review',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), nullable=True),
        sa.Column('blind_type', sa.String(length=20), nullable=True),
        sa.Column('scores', sa.JSON(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=255), nullable=True),
        sa.Column('decision', sa.String(length=50), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'assignment',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )

def downgrade():
    op.drop_table('assignment')
    op.drop_table('review')
    op.drop_table('submission')
