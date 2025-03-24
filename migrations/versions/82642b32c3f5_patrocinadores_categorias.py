"""patrocinadores categorias

Revision ID: 82642b32c3f5
Revises: 9a529b18c438
Create Date: 2025-03-22 15:35:58.867190

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '82642b32c3f5'
down_revision = '9a529b18c438'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Adicionar a coluna "categoria" como nullable=True
    with op.batch_alter_table('patrocinador', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('categoria', sa.String(length=50), nullable=True)
        )
        # Também podemos ajustar aqui o evento_id e logo_path caso deseje
        # que eles fiquem obrigatórios. Se quiser manter NOT NULL,
        # verifique se NÃO há registros antigos sem evento_id ou logo_path.

        # Se já tem certeza de que todos patrocinadores possuem
        # evento_id e logo_path não nulos, pode deixar assim:
        batch_op.alter_column('evento_id', existing_type=sa.INTEGER(), nullable=False)
        batch_op.alter_column('logo_path', existing_type=sa.VARCHAR(length=255), nullable=False)

    # 2) Preencher todos os registros existentes com um valor default de categoria
    #    (Exemplo: 'Patrocinio' ou 'Desconhecida', a seu critério)
    op.execute("UPDATE patrocinador SET categoria = 'Patrocinio' WHERE categoria IS NULL")

    # 3) Agora tornar a coluna "categoria" NOT NULL
    with op.batch_alter_table('patrocinador', schema=None) as batch_op:
        batch_op.alter_column(
            'categoria',
            existing_type=sa.String(length=50),
            nullable=False
        )


def downgrade():
    # Reverso do upgrade (remover a coluna e reverter alterações)
    with op.batch_alter_table('patrocinador', schema=None) as batch_op:
        batch_op.alter_column('logo_path', existing_type=sa.VARCHAR(length=255), nullable=True)
        batch_op.alter_column('evento_id', existing_type=sa.INTEGER(), nullable=True)
        batch_op.drop_column('categoria')
