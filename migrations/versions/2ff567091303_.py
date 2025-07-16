"""empty message

Revision ID: 2ff567091303
Revises: 2b39319b5045
Create Date: 2025-07-10 22:45:14.417237

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2ff567091303'
down_revision = '2b39319b5045'
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona apenas a FOREIGN KEY (coluna evento_id já existe)
    with op.batch_alter_table('campos_personalizados_cadastro', schema=None) as batch_op:
        batch_op.create_foreign_key(
            batch_op.f('fk_campos_personalizados_cadastro_evento_id_evento'),
            'evento', ['evento_id'], ['id']
        )

    # Nenhuma alteração segura em configuracao_evento neste ponto
    with op.batch_alter_table('configuracao_evento', schema=None) as batch_op:
        pass

    # Apenas cria FK para reviewer_application
    with op.batch_alter_table('reviewer_application', schema=None) as batch_op:
        # batch_op.create_foreign_key(
        #     batch_op.f('fk_reviewer_application_evento_id_evento'),
        #     'evento', ['evento_id'], ['id']
        # )
        pass  # FK já existente

    # Remove colunas antigas da revisão
    with op.batch_alter_table('revisao_config', schema=None) as batch_op:
        batch_op.drop_column('modelo_blind')
        batch_op.drop_column('numero_revisores')
        batch_op.drop_column('prazo_revisao')


def downgrade():
    # Restaura colunas da revisão removidas no upgrade
    with op.batch_alter_table('revisao_config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prazo_revisao', postgresql.TIMESTAMP(), nullable=True))
        batch_op.add_column(sa.Column('numero_revisores', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('modelo_blind', sa.VARCHAR(length=20), nullable=True))

    # Remove a FK de reviewer_application (não remove colunas porque não foram adicionadas aqui)
    with op.batch_alter_table('reviewer_application', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_reviewer_application_evento_id_evento'), type_='foreignkey')

    # Nenhuma ação necessária em configuracao_evento
    with op.batch_alter_table('configuracao_evento', schema=None) as batch_op:
        pass

    # Remove a FK de campos_personalizados_cadastro (não remove coluna)
    with op.batch_alter_table('campos_personalizados_cadastro', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_campos_personalizados_cadastro_evento_id_evento'), type_='foreignkey')
