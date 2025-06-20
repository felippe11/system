from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "16e80ff4acb5"
down_revision = "2bb295ff7424"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    # ------------------------------------------------------------------ SUBMISSION
    if "submission" not in inspector.get_table_names():
        op.create_table(
            "submission",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("abstract", sa.Text(), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("file_path", sa.String(255), nullable=True),
            sa.Column("locator", sa.String(36), unique=True),
            sa.Column("code_hash", sa.String(128)),
            sa.Column("status", sa.String(50)),
            sa.Column("area_id", sa.Integer()),
            sa.Column("author_id", sa.Integer()),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
    else:
        with op.batch_alter_table("submission") as batch:
            cols = {c["name"] for c in inspector.get_columns("submission")}
            if "content" not in cols:
                batch.add_column(sa.Column("content", sa.Text()))
            if "locator" not in cols:
                batch.add_column(sa.Column("locator", sa.String(36), unique=True))
            elif next(c for c in inspector.get_columns("submission") if c["name"] == "locator")["type"].length != 36:
                batch.alter_column("locator", type_=sa.String(36))
            if "code_hash" not in cols:
                batch.add_column(sa.Column("code_hash", sa.String(128)))
            elif next(c for c in inspector.get_columns("submission") if c["name"] == "code_hash")["type"].length != 128:
                batch.alter_column("code_hash", type_=sa.String(128))

    # ------------------------------------------------------------------ REVIEW
    if "review" not in inspector.get_table_names():
        op.create_table(
            "review",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("submission_id", sa.Integer(), nullable=False),
            sa.Column("reviewer_id", sa.Integer()),
            sa.Column("blind_type", sa.String(20)),
            sa.Column("scores", sa.JSON()),
            sa.Column("comments", sa.Text()),
            sa.Column("file_path", sa.String(255)),
            sa.Column("decision", sa.String(50)),
            sa.Column("submitted_at", sa.DateTime()),
        )
    # se a tabela já existir mas você precisar garantir colunas adicionais,
    # faça algo semelhante ao bloco batch_alter_table acima.

    # ------------------------------------------------------------------ ASSIGNMENT
    if "assignment" not in inspector.get_table_names():
        op.create_table(
            "assignment",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("submission_id", sa.Integer(), nullable=False),
            sa.Column("reviewer_id", sa.Integer(), nullable=False),
            sa.Column("deadline", sa.DateTime()),
            sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    # idem: use batch_alter_table se precisar ajustar colunas já existentes


def downgrade():
    # só removemos se temos certeza de que foram criadas por esta migração
    if op.get_bind().dialect.has_table(op.get_bind(), "assignment"):
        op.drop_table("assignment")
    if op.get_bind().dialect.has_table(op.get_bind(), "review"):
        op.drop_table("review")
    # não removemos submission, pois já existia antes
