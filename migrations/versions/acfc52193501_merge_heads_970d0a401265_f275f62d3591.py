"""Merge heads 970d0a401265 + f275f62d3591

Revision ID: acfc52193501
Revises: 970d0a401265, f275f62d3591
Create Date: 2025-09-02 16:06:18.451458
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'acfc52193501'
down_revision = ('970d0a401265', 'f275f62d3591')
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # === Ajuste de esquema: adicionar 'fechado' em horario_visitacao ===
    # 1) cria a coluna como NULLABLE primeiro (evita problema em tabelas grandes)
    with op.batch_alter_table('horario_visitacao') as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns("horario_visitacao")}
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("horario_visitacao")}
        if "fechado" not in existing_cols:
            batch_op.add_column(sa.Column('fechado', sa.Boolean(), nullable=True))

    # 2) backfill razoável: fechado=True quando não há vagas; caso contrário False
    op.execute("""
        UPDATE horario_visitacao
        SET fechado = CASE
            WHEN vagas_disponiveis IS NOT NULL AND vagas_disponiveis <= 0 THEN TRUE
            ELSE FALSE
        END
        WHERE fechado IS NULL
    """)

    # 3) aplicar NOT NULL + default
    with op.batch_alter_table('horario_visitacao') as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns("horario_visitacao")}
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("horario_visitacao")}
        batch_op.alter_column('fechado',
                              existing_type=sa.Boolean(),
                              nullable=False,
                              server_default=sa.text('false'))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Reversão: remover a coluna 'fechado'
    with op.batch_alter_table('horario_visitacao') as batch_op:
        existing_cols = {col['name'] for col in inspector.get_columns("horario_visitacao")}
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys("horario_visitacao")}
        batch_op.drop_column('fechado')
