"""Add assinatura field to certificado_revisor_config

Revision ID: add_assinatura_certificado_revisor
Revises: 
Create Date: 2025-09-29 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_assinatura_certificado_revisor'
down_revision = 'cert_revisor_001'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    """Add incluir_assinatura_cliente field to certificado_revisor_config table."""
    # Verificar se a coluna já existe
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'certificado_revisor_config' 
        AND column_name = 'incluir_assinatura_cliente'
    """))
    
    if not result.fetchone():
        # Adicionar a coluna
        op.add_column('certificado_revisor_config', 
                     sa.Column('incluir_assinatura_cliente', sa.Boolean(), 
                              nullable=True, server_default=sa.text('true')))
        
        # Atualizar registros existentes
        connection.execute(sa.text("""
            UPDATE certificado_revisor_config 
            SET incluir_assinatura_cliente = TRUE 
            WHERE incluir_assinatura_cliente IS NULL
        """))

def downgrade():
    """Remove incluir_assinatura_cliente field from certificado_revisor_config table."""
    op.drop_column('certificado_revisor_config', 'incluir_assinatura_cliente')
