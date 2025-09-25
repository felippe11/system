#!/usr/bin/env python3
"""
Script de migração para adicionar tabelas de lembretes de oficinas.
Execute este script para criar as tabelas necessárias no banco de dados.
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.reminder import LembreteOficina, LembreteEnvio

def create_reminder_tables():
    """Cria as tabelas de lembretes no banco de dados."""
    app = create_app()
    
    with app.app_context():
        try:
            print("Criando tabelas de lembretes...")
            
            # Criar tabelas
            db.create_all()
            
            print("✅ Tabelas de lembretes criadas com sucesso!")
            print("   - lembrete_oficina")
            print("   - lembrete_envio")
            
            # Verificar se as tabelas foram criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'lembrete_oficina' in tables and 'lembrete_envio' in tables:
                print("✅ Verificação: Tabelas encontradas no banco de dados")
            else:
                print("❌ Erro: Tabelas não foram criadas corretamente")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            return False

if __name__ == "__main__":
    print("=== MIGRAÇÃO: Tabelas de Lembretes ===")
    print()
    
    success = create_reminder_tables()
    
    if success:
        print()
        print("🎉 Migração concluída com sucesso!")
        print("   O sistema de lembretes está pronto para uso.")
    else:
        print()
        print("💥 Migração falhou!")
        print("   Verifique os logs de erro acima.")
        sys.exit(1)
