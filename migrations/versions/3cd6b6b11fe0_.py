"""empty message

Revision ID: 3cd6b6b11fe0
Revises: 36a58e54b28a
Create Date: 2025-08-22 13:28:10.035219
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = "3cd6b6b11fe0"
down_revision = "36a58e54b28a"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    cols = {c["name"] for c in inspector.get_columns(table_name)} if _has_table(inspector, table_name) else set()
    return column_name in cols


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # 1) Tabela revisor_process_evento (criar apenas se não existir)
    if not _has_table(inspector, "revisor_process_evento"):
        op.create_table(
            "revisor_process_evento",
            sa.Column("process_id", sa.Integer(), nullable=False),
            sa.Column("evento_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["evento_id"], ["evento.id"], name=op.f("fk_revisor_process_evento_evento_id_evento")
            ),
            sa.ForeignKeyConstraint(
                ["process_id"], ["revisor_process.id"], name=op.f("fk_revisor_process_evento_process_id_revisor_process")
            ),
            sa.PrimaryKeyConstraint("process_id", "evento_id", name=op.f("pk_revisor_process_evento")),
        )

    # 2) review_email_log (drop se existir)
    op.execute("DROP TABLE IF EXISTS review_email_log CASCADE;")

    # 3) evento_barema: remover unique uq_evento_barema_evento_id se existir
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM   pg_constraint c
                JOIN   pg_class t ON t.oid = c.conrelid
                WHERE  c.conname = 'uq_evento_barema_evento_id'
                AND    t.relname = 'evento_barema'
            ) THEN
                ALTER TABLE evento_barema DROP CONSTRAINT uq_evento_barema_evento_id;
            END IF;
        END$$;
        """
    )

    # 4) formularios.is_submission_form -> nullable True (idempotente na prática)
    if _has_table(inspector, "formularios") and _has_column(inspector, "formularios", "is_submission_form"):
        with op.batch_alter_table("formularios", schema=None) as batch_op:
            batch_op.alter_column(
                "is_submission_form",
                existing_type=sa.BOOLEAN(),
                nullable=True,
                existing_server_default=sa.text("false"),
            )

    # 5) revisor_process: adicionar evento_id e FK se não existirem
    if _has_table(inspector, "revisor_process"):
        if not _has_column(inspector, "revisor_process", "evento_id"):
            with op.batch_alter_table("revisor_process", schema=None) as batch_op:
                batch_op.add_column(sa.Column("evento_id", sa.Integer(), nullable=True))

        # criar FK se não existir
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM   pg_constraint c
                    JOIN   pg_class t ON t.oid = c.conrelid
                    WHERE  c.conname = 'fk_revisor_process_evento_id_evento'
                    AND    t.relname = 'revisor_process'
                ) THEN
                    ALTER TABLE revisor_process
                    ADD CONSTRAINT fk_revisor_process_evento_id_evento
                    FOREIGN KEY (evento_id) REFERENCES evento (id);
                END IF;
            END$$;
            """
        )

    # 6) revisor_process_evento_association:
    #     - add revisor_process_id se não existir
    #     - dropar FK antiga se existir
    #     - criar FK nova se não existir
    #     - dropar process_id se existir
    if _has_table(inspector, "revisor_process_evento_association"):
        with op.batch_alter_table("revisor_process_evento_association", schema=None) as batch_op:
            if not _has_column(inspector, "revisor_process_evento_association", "revisor_process_id"):
                batch_op.add_column(sa.Column("revisor_process_id", sa.Integer(), nullable=False))

        # DROP FK antiga (nome conforme sua migração original)
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM   pg_constraint c
                    JOIN   pg_class t ON t.oid = c.conrelid
                    WHERE  c.conname = 'fk_revisor_process_evento_association_process_id_reviso_3fff'
                    AND    t.relname = 'revisor_process_evento_association'
                ) THEN
                    ALTER TABLE revisor_process_evento_association
                    DROP CONSTRAINT fk_revisor_process_evento_association_process_id_reviso_3fff;
                END IF;
            END$$;
            """
        )

        # ADD FK nova se não existir
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM   pg_constraint c
                    JOIN   pg_class t ON t.oid = c.conrelid
                    WHERE  c.conname = 'fk_revisor_process_evento_association_revisor_process_id_revisor_process'
                    AND    t.relname = 'revisor_process_evento_association'
                ) THEN
                    ALTER TABLE revisor_process_evento_association
                    ADD CONSTRAINT fk_revisor_process_evento_association_revisor_process_id_revisor_process
                    FOREIGN KEY (revisor_process_id) REFERENCES revisor_process (id);
                END IF;
            END$$;
            """
        )

        # DROP coluna antiga process_id se existir
        if _has_column(inspector, "revisor_process_evento_association", "process_id"):
            with op.batch_alter_table("revisor_process_evento_association", schema=None) as batch_op:
                batch_op.drop_column("process_id")

    # 7) submission.attributes JSON se não existir
    if _has_table(inspector, "submission") and not _has_column(inspector, "submission", "attributes"):
        with op.batch_alter_table("submission", schema=None) as batch_op:
            batch_op.add_column(sa.Column("attributes", sa.JSON(), nullable=True))

    # 8) work_metadata.data JSON NOT NULL
    if _has_table(inspector, "work_metadata") and not _has_column(inspector, "work_metadata", "data"):
        # adiciona com default {} para não quebrar dados existentes e depois torna NOT NULL
        with op.batch_alter_table("work_metadata", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("data", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=True)
            )
        # remove default e aplica NOT NULL
        op.execute("ALTER TABLE work_metadata ALTER COLUMN data DROP DEFAULT;")
        op.execute("UPDATE work_metadata SET data = '{}'::json WHERE data IS NULL;")
        op.execute("ALTER TABLE work_metadata ALTER COLUMN data SET NOT NULL;")


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Reverter work_metadata.data
    if _has_table(inspector, "work_metadata") and _has_column(inspector, "work_metadata", "data"):
        with op.batch_alter_table("work_metadata", schema=None) as batch_op:
            batch_op.drop_column("data")

    # Reverter submission.attributes
    if _has_table(inspector, "submission") and _has_column(inspector, "submission", "attributes"):
        with op.batch_alter_table("submission", schema=None) as batch_op:
            batch_op.drop_column("attributes")

    # revisor_process_evento_association: voltar para process_id
    if _has_table(inspector, "revisor_process_evento_association"):
        # adicionar process_id (se não existir)
        if not _has_column(inspector, "revisor_process_evento_association", "process_id"):
            with op.batch_alter_table("revisor_process_evento_association", schema=None) as batch_op:
                batch_op.add_column(sa.Column("process_id", sa.Integer(), nullable=False))

        # dropar FK nova se existir
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM   pg_constraint c
                    JOIN   pg_class t ON t.oid = c.conrelid
                    WHERE  c.conname = 'fk_revisor_process_evento_association_revisor_process_id_revisor_process'
                    AND    t.relname = 'revisor_process_evento_association'
                ) THEN
                    ALTER TABLE revisor_process_evento_association
                    DROP CONSTRAINT fk_revisor_process_evento_association_revisor_process_id_revisor_process;
                END IF;
            END$$;
            """
        )

        # recriar FK antiga se não existir
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM   pg_constraint c
                    JOIN   pg_class t ON t.oid = c.conrelid
                    WHERE  c.conname = 'fk_revisor_process_evento_association_process_id_reviso_3fff'
                    AND    t.relname = 'revisor_process_evento_association'
                ) THEN
                    ALTER TABLE revisor_process_evento_association
                    ADD CONSTRAINT fk_revisor_process_evento_association_process_id_reviso_3fff
                    FOREIGN KEY (process_id) REFERENCES revisor_process (id);
                END IF;
            END$$;
            """
        )

        # dropar revisor_process_id se existir
        if _has_column(inspector, "revisor_process_evento_association", "revisor_process_id"):
            with op.batch_alter_table("revisor_process_evento_association", schema=None) as batch_op:
                batch_op.drop_column("revisor_process_id")

    # revisor_process: remover FK e coluna evento_id
    if _has_table(inspector, "revisor_process"):
        # drop FK se existir
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM   pg_constraint c
                    JOIN   pg_class t ON t.oid = c.conrelid
                    WHERE  c.conname = 'fk_revisor_process_evento_id_evento'
                    AND    t.relname = 'revisor_process'
                ) THEN
                    ALTER TABLE revisor_process
                    DROP CONSTRAINT fk_revisor_process_evento_id_evento;
                END IF;
            END$$;
            """
        )
        if _has_column(inspector, "revisor_process", "evento_id"):
            with op.batch_alter_table("revisor_process", schema=None) as batch_op:
                batch_op.drop_column("evento_id")

    # formularios.is_submission_form -> voltar a NOT NULL com default false
    if _has_table(inspector, "formularios") and _has_column(inspector, "formularios", "is_submission_form"):
        with op.batch_alter_table("formularios", schema=None) as batch_op:
            batch_op.alter_column(
                "is_submission_form",
                existing_type=sa.BOOLEAN(),
                nullable=False,
                existing_server_default=sa.text("false"),
            )

    # evento_barema: recriar unique uq_evento_barema_evento_id se não existir
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM   pg_constraint c
                JOIN   pg_class t ON t.oid = c.conrelid
                WHERE  c.conname = 'uq_evento_barema_evento_id'
                AND    t.relname = 'evento_barema'
            ) THEN
                ALTER TABLE evento_barema
                ADD CONSTRAINT uq_evento_barema_evento_id UNIQUE (evento_id);
            END IF;
        END$$;
        """
    )

    # recriar review_email_log se não existir (espelhando a original)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'review_email_log'
            ) THEN
                CREATE TABLE review_email_log (
                    id SERIAL PRIMARY KEY,
                    review_id INTEGER NOT NULL REFERENCES review(id),
                    recipient VARCHAR(255) NOT NULL,
                    error VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            END IF;
        END$$;
        """
    )

    # por fim, dropar revisor_process_evento (se existir)
    if _has_table(inspector, "revisor_process_evento"):
        op.drop_table("revisor_process_evento")
