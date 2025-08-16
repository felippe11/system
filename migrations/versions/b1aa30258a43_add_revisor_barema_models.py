"""add revisor barema models"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1aa30258a43'
down_revision = 'a16bd5bf6b16'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'revisor_criterio',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('process_id', sa.Integer(), sa.ForeignKey('revisor_process.id'), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
    )
    op.create_table(
        'revisor_requisito',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('criterio_id', sa.Integer(), sa.ForeignKey('revisor_criterio.id', ondelete='CASCADE'), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=False),
    )


def downgrade():
    op.drop_table('revisor_requisito')
    op.drop_table('revisor_criterio')

