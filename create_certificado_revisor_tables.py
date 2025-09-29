#!/usr/bin/env python3
"""
Script para aplicar migração de certificados de revisores.

Este script aplica a migração que cria as tabelas necessárias para o sistema de certificados de revisores:
- certificado_revisor_config: Configurações de certificados por cliente/evento
- certificado_revisor: Certificados emitidos para revisores

IMPORTANTE: Para produção, use sempre Flask-Migrate ao invés deste script.
Este script é apenas para desenvolvimento/teste local.
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db, migrate
from models import CertificadoRevisorConfig, CertificadoRevisor

def apply_migration():
    """Aplica a migração de certificados de revisores."""
    app = create_app()
    
    with app.app_context():
        try:
            print("Aplicando migração de certificados de revisores...")
            
            # Verificar se a migração já foi aplicada
            from flask_migrate import current, upgrade
            current_revision = current()
            print(f"Revisão atual: {current_revision}")
            
            # Aplicar migração
            upgrade()
            
            print("✅ Migração aplicada com sucesso!")
            print("📋 Tabelas criadas:")
            print("   - certificado_revisor_config")
            print("   - certificado_revisor")
            
        except Exception as e:
            print(f"❌ Erro ao aplicar migração: {e}")
            return False
    
    return True

def verify_tables():
    """Verifica se as tabelas foram criadas corretamente."""
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar se as tabelas existem
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['certificado_revisor_config', 'certificado_revisor']
            
            print("\n🔍 Verificando tabelas...")
            for table in required_tables:
                if table in tables:
                    print(f"✅ {table} - OK")
                else:
                    print(f"❌ {table} - FALTANDO")
                    return False
            
            print("\n✅ Todas as tabelas foram criadas corretamente!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao verificar tabelas: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Iniciando aplicação da migração de certificados de revisores...")
    print(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    print("\n⚠️  IMPORTANTE:")
    print("   Para produção, use sempre:")
    print("   flask db upgrade")
    print("   Este script é apenas para desenvolvimento/teste local.")
    print()
    
    if apply_migration():
        verify_tables()
        print("\n🎉 Migração aplicada com sucesso!")
        print("\n📝 Próximos passos:")
        print("   1. Teste a funcionalidade no dashboard do cliente")
        print("   2. Configure certificados para um evento")
        print("   3. Libere certificados para revisores")
        print("   4. Verifique se os revisores conseguem baixar os certificados")
        print("\n🚀 Para produção:")
        print("   - Execute: flask db upgrade")
        print("   - Verifique se as tabelas foram criadas no banco")
    else:
        print("\n❌ Migração falhou!")
        sys.exit(1)
