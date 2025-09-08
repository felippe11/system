"""add monitor cadastro link table

Revision ID: 414d4628e3f4
Revises: 3267ae82aadf
Create Date: 2025-09-08 18:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "414d4628e3f4"
down_revision = "3267ae82aadf"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "monitor_cadastro_link",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monitor_cadastro_link")),
        sa.UniqueConstraint("token", name=op.f("uq_monitor_cadastro_link_token")),
    )


def downgrade():
    op.drop_table("monitor_cadastro_link")
