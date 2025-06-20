"""migrate resposta_campo to resposta_formulario relationship

Revision ID: 2bb295ff7424
Revises: 66f23e77b98d
Create Date: 2025-07-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2bb295ff7424'
down_revision = '66f23e77b98d'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # obtém todos ids atualmente em respostas_campo
    ids = conn.execute(sa.text("SELECT DISTINCT resposta_formulario_id FROM respostas_campo")).fetchall()
    for (legacy_id,) in ids:
        # verifica se já existe um RespostaFormulario com esse id
        exists = conn.execute(sa.text("SELECT 1 FROM respostas_formulario WHERE id=:id"), {'id': legacy_id}).fetchone()
        if exists:
            continue
        # cria registro usando o id legado, vinculando usuario_id ao mesmo valor
        conn.execute(
            sa.text(
                "INSERT INTO respostas_formulario (id, formulario_id, usuario_id, data_submissao)"
                " VALUES (:id, 1, :usuario_id, CURRENT_TIMESTAMP)"
            ),
            {"id": legacy_id, "usuario_id": legacy_id},
        )


def downgrade():
    pass
