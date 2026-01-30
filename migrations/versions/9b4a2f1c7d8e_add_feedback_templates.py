"""add feedback templates

Revision ID: 9b4a2f1c7d8e
Revises: 27f85c2ac4a0, e05538c4af79
Create Date: 2026-01-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9b4a2f1c7d8e"
down_revision = ("27f85c2ac4a0", "e05538c4af79")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feedback_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], name="fk_feedback_templates_cliente_id_cliente"),
    )

    op.create_table(
        "feedback_template_oficina",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("oficina_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["template_id"], ["feedback_templates.id"], name="fk_feedback_template_oficina_template_id_feedback_templates"),
        sa.ForeignKeyConstraint(["oficina_id"], ["oficina.id"], name="fk_feedback_template_oficina_oficina_id_oficina"),
    )

    op.add_column(
        "perguntas_feedback",
        sa.Column("template_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_perguntas_feedback_template_id_feedback_templates",
        "perguntas_feedback",
        "feedback_templates",
        ["template_id"],
        ["id"],
    )

    op.alter_column(
        "respostas_feedback",
        "usuario_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "respostas_feedback",
        "usuario_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_constraint(
        "fk_perguntas_feedback_template_id_feedback_templates",
        "perguntas_feedback",
        type_="foreignkey",
    )
    op.drop_column("perguntas_feedback", "template_id")

    op.drop_table("feedback_template_oficina")
    op.drop_table("feedback_templates")
