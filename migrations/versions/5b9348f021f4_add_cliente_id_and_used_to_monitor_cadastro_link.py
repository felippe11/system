"""Add cliente_id and used to monitor_cadastro_link (idempotent)

Revision ID: 5b9348f021f4
Revises: 32bf7215c932
Create Date: 2025-09-08 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5b9348f021f4"
down_revision = "32bf7215c932"
branch_labels = None
depends_on = None


def _insp():
    return sa.inspect(op.get_bind())


def _get_columns(table_name: str) -> dict[str, dict]:
    """Retorna dict {col_name: col_info}"""
    insp = _insp()
    cols = {}
    for col in insp.get_columns(table_name):
        cols[col["name"]] = col
    return cols


def _fk_exists(table_name: str, name: str | None = None,
               constrained_columns: list[str] | None = None,
               referred_table: str | None = None) -> bool:
    insp = _insp()
    for fk in insp.get_foreign_keys(table_name):
        if name and fk.get("name") == name:
            return True
        if referred_table and fk.get("referred_table") != referred_table:
            continue
        if constrained_columns:
            if set(fk.get("constrained_columns") or []) == set(constrained_columns):
                return True
    return False


def upgrade():
    table = "monitor_cadastro_link"
    cols = _get_columns(table)

    # 1) cliente_id (NOT NULL) — cria apenas se não existir
    if "cliente_id" not in cols:
        op.add_column(
            table,
            sa.Column("cliente_id", sa.Integer(), nullable=False),
        )
        # Opcional: se a tabela tiver linhas e você precisar preencher valores,
        # crie aqui uma data migration antes de tornar NOT NULL.

    # 2) used (BOOLEAN) — cria apenas se não existir
    if "used" not in cols:
        op.add_column(
            table,
            sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        # Remover server_default após criação (mantém NOT NULL com default no schema limpo)
        op.alter_column(table, "used", server_default=None)

    # 3) token length (VARCHAR(36)) — altera apenas se precisar
    token_info = cols.get("token")
    if token_info:
        current_len = getattr(token_info.get("type"), "length", None)
        # Só altera se o length não for 36
        if current_len != 36:
            op.alter_column(
                table,
                "token",
                existing_type=sa.String(length=current_len) if current_len else sa.String(),
                type_=sa.String(length=36),
                existing_nullable=not token_info.get("nullable", False) is False,
            )

    # 4) FK cliente_id -> cliente(id) — cria apenas se não existir
    fk_name = "fk_monitor_cadastro_link_cliente_id_cliente"
    if not _fk_exists(table, name=fk_name) and not _fk_exists(
        table, constrained_columns=["cliente_id"], referred_table="cliente"
    ):
        op.create_foreign_key(
            fk_name,
            source_table=table,
            referent_table="cliente",
            local_cols=["cliente_id"],
            remote_cols=["id"],
        )


def downgrade():
    table = "monitor_cadastro_link"

    # 1) Drop FK se existir
    fk_name = "fk_monitor_cadastro_link_cliente_id_cliente"
    if _fk_exists(table, name=fk_name) or _fk_exists(
        table, constrained_columns=["cliente_id"], referred_table="cliente"
    ):
        op.drop_constraint(fk_name, table, type_="foreignkey")

    cols = _get_columns(table)

    # 2) Reverter token length para 255 apenas se atualmente for 36
    token_info = cols.get("token")
    if token_info:
        current_len = getattr(token_info.get("type"), "length", None)
        if current_len == 36:
            op.alter_column(
                table,
                "token",
                existing_type=sa.String(length=36),
                type_=sa.String(length=255),
                existing_nullable=not token_info.get("nullable", False) is False,
            )

    # 3) Remover used se existir
    cols = _get_columns(table)  # re-leitura
    if "used" in cols:
        op.drop_column(table, "used")

    # 4) Remover cliente_id se existir
    cols = _get_columns(table)  # re-leitura
    if "cliente_id" in cols:
        op.drop_column(table, "cliente_id")
