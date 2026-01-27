"""add max_trabalhos_por_revisor

Revision ID: 64f77f3899ea
Revises: e4cb3d4630b1
Create Date: 2025-08-14 22:45:28.829816

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '64f77f3899ea'
down_revision = 'e4cb3d4630b1'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("configuracao_cliente"):
        return
    op.add_column(
        "configuracao_cliente",
        sa.Column(
            "max_trabalhos_por_revisor",
            sa.Integer(),
            nullable=True,
            server_default="5",
        ),
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("configuracao_cliente"):
        return
    op.drop_column("configuracao_cliente", "max_trabalhos_por_revisor")
