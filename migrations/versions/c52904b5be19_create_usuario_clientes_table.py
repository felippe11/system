"""create usuario_clientes association table

Revision ID: c52904b5be19
Revises: 2ff567091303
Create Date: 2026-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = 'c52904b5be19'
down_revision = '2ff567091303'
branch_labels = None
depends_on = None

TABLE = 'usuario_clientes'


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if TABLE not in insp.get_table_names():
        op.create_table(
            TABLE,
            sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuario.id'), primary_key=True),
            sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('cliente.id'), primary_key=True),
        )

    bind.execute(text(
        f"INSERT INTO {TABLE} (usuario_id, cliente_id) "
        "SELECT id, cliente_id FROM usuario WHERE cliente_id IS NOT NULL"
    ))


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if TABLE in insp.get_table_names():
        op.drop_table(TABLE)
