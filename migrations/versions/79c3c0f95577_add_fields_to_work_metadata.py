"""add fields to work_metadata

Revision ID: 79c3c0f95577
Revises: b7f45c8e9d1a
Create Date: 2025-02-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "79c3c0f95577"
down_revision = "b7f45c8e9d1a"
branch_labels = None
depends_on = None

TABLE = "work_metadata"
FK_NAME = "fk_work_metadata_evento"
FK_COL = "evento_id"

ADDED_COLS = [
    sa.Column("titulo", sa.String(length=255), nullable=True),
    sa.Column("categoria", sa.String(length=100), nullable=True),
    sa.Column("rede_ensino", sa.String(length=100), nullable=True),
    sa.Column("etapa_ensino", sa.String(length=100), nullable=True),
    sa.Column("pdf_url", sa.String(length=255), nullable=True),
    sa.Column(FK_COL, sa.Integer(), nullable=True),
]

# Para checagem simples no downgrade
ADDED_COL_NAMES = {"titulo", "categoria", "rede_ensino", "etapa_ensino", "pdf_url", FK_COL}
ALL_CREATED_COLS_IF_NEW = {"id"} | ADDED_COL_NAMES


def _has_table(insp, table_name: str) -> bool:
    return table_name in insp.get_table_names()


def _table_columns(insp, table_name: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table_name)} if _has_table(insp, table_name) else set()


def _has_column(insp, table_name: str, col: str) -> bool:
    return col in _table_columns(insp, table_name)


def _fk_names(insp, table_name: str) -> set[str]:
    return {fk["name"] for fk in insp.get_foreign_keys(table_name)} if _has_table(insp, table_name) else set()


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    if not _has_table(insp, TABLE):
        # Tabela não existe: cria já com todas as colunas e FK
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("titulo", sa.String(length=255), nullable=True),
            sa.Column("categoria", sa.String(length=100), nullable=True),
            sa.Column("rede_ensino", sa.String(length=100), nullable=True),
            sa.Column("etapa_ensino", sa.String(length=100), nullable=True),
            sa.Column("pdf_url", sa.String(length=255), nullable=True),
            sa.Column(FK_COL, sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint([FK_COL], ["evento.id"], name=FK_NAME),
        )
        return

    # Tabela já existe: adiciona colunas que faltam
    existing_cols = _table_columns(insp, TABLE)

    for col in ADDED_COLS:
        if col.name not in existing_cols:
            op.add_column(TABLE, col)

    # Garante a FK se não existir
    if FK_NAME not in _fk_names(insp, TABLE):
        # Confere novamente se a coluna FK existe (pode ter sido criada acima)
        if not _has_column(insp, TABLE, FK_COL):
            op.add_column(TABLE, sa.Column(FK_COL, sa.Integer(), nullable=True))
        op.create_foreign_key(FK_NAME, TABLE, "evento", [FK_COL], ["id"])


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    if not _has_table(insp, TABLE):
        # Nada a fazer
        return

    # Se a tabela foi criada inteiramente por esta migração (ou só contém o conjunto que criamos),
    # é seguro derrubá-la por completo.
    cols_now = _table_columns(insp, TABLE)
    if cols_now.issubset(ALL_CREATED_COLS_IF_NEW):
        # Remover tabela inteira (dropará também constraints)
        op.drop_table(TABLE)
        return

    # Caso contrário, desfazemos apenas o que esta migração adicionou.
    # 1) Remove a FK se existir
    if FK_NAME in _fk_names(insp, TABLE):
        op.drop_constraint(FK_NAME, TABLE, type_="foreignkey")

    # 2) Remove as colunas adicionadas (se existirem), na ordem inversa
    #    (FK_COL por último já caiu a FK acima).
    drop_order = ["pdf_url", "etapa_ensino", "rede_ensino", "categoria", "titulo", FK_COL]
    for col_name in drop_order:
        if _has_column(insp, TABLE, col_name):
            op.drop_column(TABLE, col_name)
