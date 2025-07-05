"""unify evento_formulario association

Revision ID: 123456789abc
Revises: ffbc68259c84
Create Date: 2025-07-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# ────────────────────────────────────────────────────────────
revision = "123456789abc"
down_revision = "ffbc68259c84"
branch_labels = None
depends_on = None
# ────────────────────────────────────────────────────────────

TARGET = "evento_formulario_association"          # nome definitivo
LEGACY = ["evento_formulario",                    # nomes antigos
          "formulario_evento_association"]


def _table_exists(bind, name: str) -> bool:
    """True se a tabela existir no banco atual."""
    return name in sa.inspect(bind).get_table_names()


# -------------------------- upgrade ------------------------- #
def upgrade() -> None:
    bind = op.get_bind()

    # 1) Nada a fazer se o nome definitivo já existe
    if _table_exists(bind, TARGET):
        return

    # 2) Renomeia a primeira variação antiga encontrada
    for old in LEGACY:
        if _table_exists(bind, old):
            op.rename_table(old, TARGET)
            break

    # 3) Se não havia nenhuma tabela legada, cria do zero
    if not _table_exists(bind, TARGET):
        op.create_table(
            TARGET,
            sa.Column(
                "evento_id",
                sa.Integer,
                sa.ForeignKey("evento.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "formulario_id",
                sa.Integer,
                sa.ForeignKey("formularios.id", ondelete="CASCADE"),
                primary_key=True,
            ),
        )


# ------------------------- downgrade ------------------------ #
def downgrade() -> None:
    """
    Volta para o primeiro nome histórico ('evento_formulario').
    - Se ele já existir, apenas remove o TARGET para não colidir.
    """
    bind = op.get_bind()

    if not _table_exists(bind, TARGET):
        return

    if _table_exists(bind, "evento_formulario"):
        op.drop_table(TARGET)
    else:
        op.rename_table(TARGET, "evento_formulario")
