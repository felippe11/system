"""empty message

Revision ID: dfb0186af775
Revises: f09857675d5a
Create Date: 2025-09-03 01:13:57.682443

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'dfb0186af775'
down_revision = 'f09857675d5a'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Create new table for auto distribution logs
    if not inspector.has_table("auto_distribution_log"):
        op.create_table(
            'auto_distribution_log',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('evento_id', sa.Integer(), nullable=False),
            sa.Column('total_submissions', sa.Integer(), nullable=False),
            sa.Column('total_assignments', sa.Integer(), nullable=False),
            sa.Column('distribution_seed', sa.String(length=50), nullable=True),
            sa.Column('conflicts_detected', sa.Integer(), nullable=True),
            sa.Column('fallback_assignments', sa.Integer(), nullable=True),
            sa.Column('failed_assignments', sa.Integer(), nullable=True),
            sa.Column('distribution_details', sa.JSON(), nullable=True),
            sa.Column('error_log', sa.JSON(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ['evento_id'], ['evento.id'], name=op.f('fk_auto_distribution_log_evento_id_evento')
            ),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_auto_distribution_log')),
        )

    # Drop legacy distribution_log table if it exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'distribution_log' in inspector.get_table_names():
        op.drop_table('distribution_log')

    # Safely add columns to revisor_process with defaults to satisfy NOT NULL
    with op.batch_alter_table('revisor_process', schema=None) as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns("revisor_process")}
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("revisor_process")}
        batch_op.add_column(
            sa.Column('nome', sa.String(length=255), nullable=False, server_default='')
        )
        if "descricao" not in existing_cols:
            batch_op.add_column(sa.Column('descricao', sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column('status', sa.String(length=50), nullable=False, server_default='ativo')
        )

    # Note: Skipping autogeneration changes to 'assignment' and 'respostas_formulario'
    # as they conflict with current models and could break existing data.


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Drop columns from revisor_process
    with op.batch_alter_table('revisor_process', schema=None) as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns("revisor_process")}
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("revisor_process")}
        batch_op.drop_column('status')
        batch_op.drop_column('descricao')
        batch_op.drop_column('nome')

    # Restore legacy distribution_log and drop new table
    op.create_table(
        'distribution_log',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('evento_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('total_submissions', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('total_assignments', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('distribution_seed', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
        sa.Column('conflicts_detected', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('fallback_assignments', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('failed_assignments', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('distribution_details', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('error_log', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('started_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('completed_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('duration_seconds', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['evento_id'], ['evento.id'], name='fk_distribution_log_evento_id_evento'),
        sa.PrimaryKeyConstraint('id', name='pk_distribution_log'),
    )
    op.drop_table('auto_distribution_log')
