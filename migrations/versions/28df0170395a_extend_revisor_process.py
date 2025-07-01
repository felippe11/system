"""extend RevisorProcess with new columns

Revision ID: 28df0170395a
Revises: 26243c055ce7, f123456789ab
Create Date: 2025-10-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "28df0170395a"
down_revision = ("26243c055ce7", "f123456789ab")
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("revisor_process", schema=None) as batch_op:
        batch_op.add_column(sa.Column("titulo", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("inicio_disponibilidade", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("fim_disponibilidade", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "exibir_para_participantes",
                sa.Boolean(),
                nullable=True,
                server_default=sa.false(),
            )
        )


def downgrade():
    with op.batch_alter_table("revisor_process", schema=None) as batch_op:
        batch_op.drop_column("exibir_para_participantes")
        batch_op.drop_column("fim_disponibilidade")
        batch_op.drop_column("inicio_disponibilidade")
        batch_op.drop_column("titulo")

