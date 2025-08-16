"""add barema models

Revision ID: 97ff1ac3c1dc
Revises: a16bd5bf6b16
Create Date: 2025-08-16 13:49:31.166484

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "97ff1ac3c1dc"
down_revision = "a16bd5bf6b16"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "barema",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["revisor_process.id"]),
        sa.UniqueConstraint("process_id"),
    )
    op.create_table(
        "barema_requisito",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("barema_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column(
            "pontuacao_min", sa.Numeric(5, 2), nullable=False, server_default="0"
        ),
        sa.Column("pontuacao_max", sa.Numeric(5, 2), nullable=False),
        sa.ForeignKeyConstraint(["barema_id"], ["barema.id"]),
    )


def downgrade():
    op.drop_table("barema_requisito")
    op.drop_table("barema")
