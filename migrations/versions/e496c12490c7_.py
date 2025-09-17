"""empty message

Revision ID: e496c12490c7
Revises: 931a82d6224c
Create Date: 2025-09-16 12:46:05.728028
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e496c12490c7"
down_revision = "931a82d6224c"
branch_labels = None
depends_on = None


def _has_table(insp, table_name: str) -> bool:
    try:
        return insp.has_table(table_name)
    except Exception:
        # Fallback para engines antigos
        return table_name in insp.get_table_names()


def _has_column(insp, table_name: str, column_name: str) -> bool:
    try:
        cols = insp.get_columns(table_name)
    except Exception:
        return False
    return any(c["name"] == column_name for c in cols)


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # ----- formador_polo -----
    # Cria a tabela somente se não existir (evita DuplicateTable após merges).
    if not _has_table(insp, "formador_polo"):
        op.create_table(
            "formador_polo",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("formador_id", sa.Integer(), nullable=False),
            sa.Column("polo_id", sa.Integer(), nullable=False),
            sa.Column("data_atribuicao", sa.DateTime(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=True),
            sa.ForeignKeyConstraint(
                ["formador_id"],
                ["ministrante.id"],
                name=op.f("fk_formador_polo_formador_id_ministrante"),
            ),
            sa.ForeignKeyConstraint(
                ["polo_id"], ["polo.id"], name=op.f("fk_formador_polo_polo_id_polo")
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_formador_polo")),
        )
    # Caso já exista, não faz nada aqui.

    # ----- solicitacao_material_formador -----
    # Adiciona colunas somente se não existirem.
    table_smf = "solicitacao_material_formador"
    add_created_at = not _has_column(insp, table_smf, "created_at")
    add_updated_at = not _has_column(insp, table_smf, "updated_at")

    if add_created_at or add_updated_at:
        with op.batch_alter_table(table_smf, schema=None) as batch_op:
            if add_created_at:
                batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
            if add_updated_at:
                batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # ----- solicitacao_material_formador -----
    table_smf = "solicitacao_material_formador"
    # Só remove as colunas se existirem para evitar erros em caminhos alternativos de downgrade.
    drop_updated_at = _has_column(insp, table_smf, "updated_at")
    drop_created_at = _has_column(insp, table_smf, "created_at")

    if drop_updated_at or drop_created_at:
        with op.batch_alter_table(table_smf, schema=None) as batch_op:
            if drop_updated_at:
                batch_op.drop_column("updated_at")
            if drop_created_at:
                batch_op.drop_column("created_at")

    # ----- formador_polo -----
    # Só dropa a tabela se existir.
    if _has_table(insp, "formador_polo"):
        op.drop_table("formador_polo")
