"""empty message

Revision ID: 8d8534bb7a94
Revises: c52904b5be19
Create Date: 2025-07-16 15:44:47.171920
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text  # IMPORTANTE para comandos SQL diretos


# revision identifiers, used by Alembic.
revision = '8d8534bb7a94'
down_revision = 'c52904b5be19'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Drop table if exists: formulario_evento_association
    result = conn.execute(text("SELECT to_regclass('formulario_evento_association')")).scalar()
    if result:
        op.drop_table('formulario_evento_association')

    # Drop table if exists: evento_formulario
    result = conn.execute(text("SELECT to_regclass('evento_formulario')")).scalar()
    if result:
        op.drop_table('evento_formulario')

    # Tornar evento_id obrigatório em campos_personalizados_cadastro
    with op.batch_alter_table('campos_personalizados_cadastro') as batch_op:
        batch_op.alter_column(
            'evento_id',
            existing_type=sa.INTEGER(),
            nullable=False
        )

    # Alterações na reviewer_application
    with op.batch_alter_table('reviewer_application') as batch_op:
        batch_op.alter_column(
            'numero_revisores',
            existing_type=sa.INTEGER(),
            nullable=True,
            existing_server_default=sa.text('2')
        )
        batch_op.alter_column(
            'modelo_blind',
            existing_type=sa.VARCHAR(length=20),
            nullable=True,
            existing_server_default=sa.text("'single'::character varying")
        )

    # Novos campos para revisao_config
    with op.batch_alter_table('revisao_config') as batch_op:
        batch_op.add_column(sa.Column('permitir_checkin_global', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('habilitar_feedback', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('habilitar_certificado_individual', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('habilitar_qrcode_evento_credenciamento', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('habilitar_submissao_trabalhos', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('mostrar_taxa', sa.Boolean(), nullable=True))


def downgrade():
    # Remover colunas da revisao_config
    with op.batch_alter_table('revisao_config') as batch_op:
        batch_op.drop_column('mostrar_taxa')
        batch_op.drop_column('habilitar_submissao_trabalhos')
        batch_op.drop_column('habilitar_qrcode_evento_credenciamento')
        batch_op.drop_column('habilitar_certificado_individual')
        batch_op.drop_column('habilitar_feedback')
        batch_op.drop_column('permitir_checkin_global')

    # Reverter alterações em reviewer_application
    with op.batch_alter_table('reviewer_application') as batch_op:
        batch_op.alter_column(
            'modelo_blind',
            existing_type=sa.VARCHAR(length=20),
            nullable=False,
            existing_server_default=sa.text("'single'::character varying")
        )
        batch_op.alter_column(
            'numero_revisores',
            existing_type=sa.INTEGER(),
            nullable=False,
            existing_server_default=sa.text('2')
        )

    # Tornar evento_id opcional novamente
    with op.batch_alter_table('campos_personalizados_cadastro') as batch_op:
        batch_op.alter_column(
            'evento_id',
            existing_type=sa.INTEGER(),
            nullable=True
        )

    # Recria evento_formulario
    op.create_table(
        'evento_formulario',
        sa.Column('evento_id', sa.INTEGER(), nullable=False),
        sa.Column('formulario_id', sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(['evento_id'], ['evento.id'], name='fk_evento_formulario_evento_id_evento'),
        sa.ForeignKeyConstraint(['formulario_id'], ['formularios.id'], name='fk_evento_formulario_formulario_id_formularios'),
        sa.PrimaryKeyConstraint('evento_id', 'formulario_id', name='pk_evento_formulario')
    )

    # Recria formulario_evento_association
    op.create_table(
        'formulario_evento_association',
        sa.Column('formulario_id', sa.INTEGER(), nullable=False),
        sa.Column('evento_id', sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(['evento_id'], ['evento.id'], name='fk_formulario_evento_association_evento_id_evento'),
        sa.ForeignKeyConstraint(['formulario_id'], ['formularios.id'], name='fk_formulario_evento_association_formulario_id_formularios'),
        sa.PrimaryKeyConstraint('formulario_id', 'evento_id', name='pk_formulario_evento_association')
    )
