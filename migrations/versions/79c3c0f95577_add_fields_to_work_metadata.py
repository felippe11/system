"""add fields to work_metadata (idempotente)

Revision ID: 79c3c0f95577
Revises: b7f45c8e9d1a
Create Date: 2025-02-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

# revision identifiers, used by Alembic.
revision = "79c3c0f95577"
down_revision = "b7f45c8e9d1a"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    insp = sa.inspect(bind)
    try:
        return insp.has_table(name)
    except ProgrammingError:
        return False


def _column_names(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    try:
        return {c["name"] for c in insp.get_columns(table)}
    except ProgrammingError:
        return set()


def _fk_exists(bind, table: str, constraint_name: str) -> bool:
    # Funciona no Postgres
    try:
        res = bind.execute(
            text(
                """
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = :table
                  AND constraint_name = :name
                  AND constraint_type = 'FOREIGN KEY'
                """
            ),
            {"table": table, "name": constraint_name},
        ).fetchone()
        return res is not None
    except Exception:
        # Em outros dialetos, se der erro, assume que não existe.
        return False


def upgrade() -> None:
    bind = op.get_bind()

    # Esquema alvo desta migração
    # (mantive exatamente as colunas que você definiu)
    spec = [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("titulo", sa.String(length=255), nullable=True),
        sa.Column("categoria", sa.String(length=100), nullable=True),
        sa.Column("rede_ensino", sa.String(length=100), nullable=True),
        sa.Column("etapa_ensino", sa.String(length=100), nullable=True),
        sa.Column("pdf_url", sa.String(length=255), nullable=True),
        sa.Column("evento_id", sa.Integer(), nullable=True),
    ]

    if not _table_exists(bind, "work_metadata"):
        # Cria a tabela completa
        op.create_table("work_metadata", *spec)
    else:
        # Garante apenas as colunas que estiverem faltando
        existing = _column_names(bind, "work_metadata")
        with op.batch_alter_table("work_metadata") as batch_op:
            for col in spec:
                if col.name == "id":
                    continue
                if col.name not in existing:
                    batch_op.add_column(col.copy())  # type: ignore

    # Cria a FK se ainda não existir e se a tabela work_metadata existe
    if _table_exists(bind, "work_metadata") and not _fk_exists(bind, "work_metadata", "fk_work_metadata_evento"):
        with op.batch_alter_table("work_metadata") as batch_op:
            batch_op.create_foreign_key(
                "fk_work_metadata_evento",
                referent_table="evento",
                local_cols=["evento_id"],
                remote_cols=["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "work_metadata"):
        return

    # Remove a FK se existir
    if _fk_exists(bind, "work_metadata", "fk_work_metadata_evento"):
        with op.batch_alter_table("work_metadata") as batch_op:
            batch_op.drop_constraint("fk_work_metadata_evento", type_="foreignkey")

    # Heurística: se a tabela contém apenas id + colunas desta migração, podemos derrubar a tabela;
    # caso contrário, só removemos as colunas adicionadas aqui.
    existing = _column_names(bind, "work_metadata")
    our_cols = {"titulo", "categoria", "rede_ensino", "etapa_ensino", "pdf_url", "evento_id"}

    if existing.issubset(our_cols.union({"id"})):
        op.drop_table("work_metadata")
    else:
        with op.batch_alter_table("work_metadata") as batch_op:
            for name in sorted(our_cols):
                if name in existing:
                    batch_op.drop_column(name)
