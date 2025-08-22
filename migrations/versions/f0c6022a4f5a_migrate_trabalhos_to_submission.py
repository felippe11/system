"""migrate trabalhos_cientificos to submission

Revision ID: f0c6022a4f5a
Revises: e92834c1b6a3
Create Date: 2025-08-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import uuid
from werkzeug.security import generate_password_hash
import json


# revision identifiers, used by Alembic.
revision = "f0c6022a4f5a"
down_revision = "e92834c1b6a3"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT id, titulo, resumo, arquivo_pdf, area_tematica, locator,
                   status, usuario_id, evento_id
            FROM trabalhos_cientificos
            """
        )
    ).fetchall()

    for row in rows:
        code = uuid.uuid4().hex[:8]
        attrs = (
            json.dumps({"area_tematica": row.area_tematica})
            if row.area_tematica
            else None
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO submission (
                    id, title, abstract, file_path, locator, status,
                    author_id, evento_id, code_hash, attributes
                ) VALUES (
                    :id, :title, :abstract, :file_path, :locator, :status,
                    :author_id, :evento_id, :code_hash, :attributes
                )
                """
            ),
            {
                "id": row.id,
                "title": row.titulo,
                "abstract": row.resumo,
                "file_path": row.arquivo_pdf,
                "locator": row.locator,
                "status": row.status,
                "author_id": row.usuario_id,
                "evento_id": row.evento_id,
                "code_hash": generate_password_hash(code, method="pbkdf2:sha256"),
                "attributes": attrs,
            },
        )

    op.drop_table("avaliacao_trabalho")
    op.drop_table("apresentacao_trabalho")
    op.drop_table("trabalhos_cientificos")


def downgrade():
    op.create_table(
        "trabalhos_cientificos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("resumo", sa.Text, nullable=True),
        sa.Column("arquivo_pdf", sa.String(length=255), nullable=True),
        sa.Column("area_tematica", sa.String(length=100), nullable=True),
        sa.Column("locator", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("usuario_id", sa.Integer, nullable=False),
        sa.Column("evento_id", sa.Integer, nullable=False),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT id, title, abstract, file_path, locator, status,
                   author_id, evento_id, attributes
            FROM submission
            """
        )
    ).fetchall()

    for row in rows:
        attrs = row.attributes or {}
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except Exception:
                attrs = {}
        area = attrs.get("area_tematica")
        conn.execute(
            sa.text(
                """
                INSERT INTO trabalhos_cientificos (
                    id, titulo, resumo, arquivo_pdf, area_tematica,
                    locator, status, usuario_id, evento_id
                ) VALUES (
                    :id, :titulo, :resumo, :arquivo_pdf, :area,
                    :locator, :status, :usuario, :evento
                )
                """
            ),
            {
                "id": row.id,
                "titulo": row.title,
                "resumo": row.abstract,
                "arquivo_pdf": row.file_path,
                "area": area,
                "locator": row.locator,
                "status": row.status,
                "usuario": row.author_id,
                "evento": row.evento_id,
            },
        )

    op.create_table("avaliacao_trabalho", sa.Column("id", sa.Integer, primary_key=True))
    op.create_table(
        "apresentacao_trabalho", sa.Column("id", sa.Integer, primary_key=True)
    )
