#!/usr/bin/env python3
"""
Script para adicionar campo de assinatura opcional aos certificados de revisores.
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def add_assinatura_field():
    """Adiciona o campo incluir_assinatura_cliente à tabela certificado_revisor_config."""
    try:
        from app import create_app
        from extensions import db
        
        app = create_app()
        
        with app.app_context():
            print("🔧 ADICIONANDO CAMPO DE ASSINATURA AOS CERTIFICADOS DE REVISORES")
            print("=" * 60)
            
            # Verificar se a coluna já existe
            result = db.engine.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'certificado_revisor_config' 
                AND column_name = 'incluir_assinatura_cliente'
            """)
            
            if result.fetchone():
                print("✅ Campo 'incluir_assinatura_cliente' já existe!")
                return
            
            # Adicionar a coluna
            print("📝 Adicionando campo 'incluir_assinatura_cliente'...")
            
            db.engine.execute("""
                ALTER TABLE certificado_revisor_config 
                ADD COLUMN incluir_assinatura_cliente BOOLEAN DEFAULT TRUE
            """)
            
            print("✅ Campo adicionado com sucesso!")
            
            # Verificar se foi criado
            result = db.engine.execute("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns 
                WHERE table_name = 'certificado_revisor_config' 
                AND column_name = 'incluir_assinatura_cliente'
            """)
            
            row = result.fetchone()
            if row:
                print(f"📊 Campo criado:")
                print(f"   Nome: {row[0]}")
                print(f"   Tipo: {row[1]}")
                print(f"   Padrão: {row[2]}")
            
            # Atualizar registros existentes para manter compatibilidade
            print("🔄 Atualizando registros existentes...")
            
            db.engine.execute("""
                UPDATE certificado_revisor_config 
                SET incluir_assinatura_cliente = TRUE 
                WHERE incluir_assinatura_cliente IS NULL
            """)
            
            print("✅ Registros existentes atualizados!")
            
            print("\n🎯 RESUMO:")
            print("   • Campo 'incluir_assinatura_cliente' adicionado")
            print("   • Valor padrão: TRUE (assinatura incluída)")
            print("   • Registros existentes atualizados")
            print("   • Sistema pronto para uso!")
            
    except Exception as e:
        print(f"❌ Erro ao adicionar campo: {e}")
        import traceback
        traceback.print_exc()

def create_migration_file():
    """Cria arquivo de migration para produção."""
    migration_content = '''"""Add assinatura field to certificado_revisor_config

Revision ID: add_assinatura_certificado_revisor
Revises: 
Create Date: 2025-09-29 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_assinatura_certificado_revisor'
down_revision = None  # Ajustar conforme necessário
branch_labels = None
depends_on = None

def upgrade():
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
'''
    
    migration_file = 'migrations/versions/add_assinatura_certificado_revisor.py'
    
    # Criar diretório se não existir
    os.makedirs(os.path.dirname(migration_file), exist_ok=True)
    
    with open(migration_file, 'w', encoding='utf-8') as f:
        f.write(migration_content)
    
    print(f"📄 Migration criada: {migration_file}")
    print("📋 Para aplicar em produção, execute:")
    print("   flask db upgrade")

if __name__ == "__main__":
    print("🚀 INICIANDO ADIÇÃO DE CAMPO DE ASSINATURA")
    print("=" * 50)
    
    # Adicionar campo ao banco
    add_assinatura_field()
    
    print("\n" + "=" * 50)
    
    # Criar migration para produção
    create_migration_file()
    
    print("\n✅ PROCESSO CONCLUÍDO!")
    print("📋 Próximos passos:")
    print("   1. Testar funcionalidade no ambiente de desenvolvimento")
    print("   2. Aplicar migration em produção: flask db upgrade")
    print("   3. Verificar se certificados estão sendo gerados corretamente")

