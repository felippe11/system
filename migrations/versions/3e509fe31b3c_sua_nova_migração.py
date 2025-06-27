"""sua nova migração

Revision ID: 3e509fe31b3c
Revises: 32b5e5b73833
Create Date: 2025-06-26 17:16:35.167329
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3e509fe31b3c"
down_revision = "32b5e5b73833"
branch_labels = None
depends_on = None


def upgrade():
    # --- CHECKIN -----------------------------------------------------------
    # Remover constraints antigas e novas se existirem
    op.execute("ALTER TABLE checkin DROP CONSTRAINT IF EXISTS checkin_usuario_id_fkey")
    op.execute("ALTER TABLE checkin DROP CONSTRAINT IF EXISTS fk_checkin_usuario_id_usuario")
    
    with op.batch_alter_table("checkin") as batch_op:
        batch_op.create_foreign_key(
            batch_op.f("fk_checkin_usuario_id_usuario"),
            "usuario",
            ["usuario_id"],
            ["id"],
        )

    # --- INSCRICAO ---------------------------------------------------------
    # Remover constraints antigas e novas se existirem
    op.execute("ALTER TABLE inscricao DROP CONSTRAINT IF EXISTS inscricao_usuario_id_fkey")
    op.execute("ALTER TABLE inscricao DROP CONSTRAINT IF EXISTS fk_inscricao_usuario_id_usuario")
    
    with op.batch_alter_table("inscricao") as batch_op:
        batch_op.create_foreign_key(
            batch_op.f("fk_inscricao_usuario_id_usuario"),
            "usuario",
            ["usuario_id"],
            ["id"],
        )

    # --- REVIEW ------------------------------------------------------------
    # Remover constraints antigas e novas se existirem
    op.execute("ALTER TABLE review DROP CONSTRAINT IF EXISTS review_reviewer_id_fkey")
    op.execute("ALTER TABLE review DROP CONSTRAINT IF EXISTS fk_review_reviewer_id_usuario")
    
    with op.batch_alter_table("review") as batch_op:
        batch_op.create_foreign_key(
            batch_op.f("fk_review_reviewer_id_usuario"),
            "usuario",
            ["reviewer_id"],
            ["id"],
        )


def downgrade():
    # --- REVIEW ------------------------------------------------------------
    # Remover constraint nova se existir
    op.execute("ALTER TABLE review DROP CONSTRAINT IF EXISTS fk_review_reviewer_id_usuario")
    
    with op.batch_alter_table("review") as batch_op:
        batch_op.create_foreign_key(
            "review_reviewer_id_fkey",
            "usuario",
            ["reviewer_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # --- INSCRICAO ---------------------------------------------------------
    # Remover constraint nova se existir
    op.execute("ALTER TABLE inscricao DROP CONSTRAINT IF EXISTS fk_inscricao_usuario_id_usuario")
    
    with op.batch_alter_table("inscricao") as batch_op:
        batch_op.create_foreign_key(
            "inscricao_usuario_id_fkey",
            "usuario",
            ["usuario_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # --- CHECKIN -----------------------------------------------------------
    # Remover constraint nova se existir
    op.execute("ALTER TABLE checkin DROP CONSTRAINT IF EXISTS fk_checkin_usuario_id_usuario")
    
    with op.batch_alter_table("checkin") as batch_op:
        batch_op.create_foreign_key(
            "checkin_usuario_id_fkey",
            "usuario",
            ["usuario_id"],
            ["id"],
            ondelete="CASCADE",
        )
