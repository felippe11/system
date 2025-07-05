"""add evento_formulario association

Revision ID: d33e6d59d2e3
Revises: 7d9bf72dc081
Create Date: 2025-07-05 04:08:30.657683

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision = "d33e6d59d2e3"
down_revision = "7d9bf72dc081"
branch_labels = None
depends_on = None

TABLE_NAME = "evento_formulario"


def _table_exists(bind, name: str) -> bool:
    inspector = reflection.Inspector.from_engine(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    """Cria a tabela evento_formulario se ela ainda não existir."""
    bind = op.get_bind()

    if not _table_exists(bind, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("evento_id", sa.Integer(), sa.ForeignKey("evento.id"), primary_key=True),
            sa.Column("formulario_id", sa.Integer(), sa.ForeignKey("formularios.id"), primary_key=True),
        )
    # Se a tabela já existe, não fazemos nada — evitamos DuplicateTable


def downgrade() -> None:
    """Remove a tabela se ela existir (opcional)."""
    bind = op.get_bind()

    if _table_exists(bind, TABLE_NAME):
        op.drop_table(TABLE_NAME)
