#!/usr/bin/env python3
"""
Script para adicionar a coluna intervalo_entrada à tabela configuracao_agendamento.
Este script deve ser executado uma vez para atualizar o banco de dados existente.
"""

import sys
import os

# Adicionar o diretório raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

def add_intervalo_entrada_column():
    """Adiciona a coluna intervalo_entrada à tabela configuracao_agendamento."""
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar se a coluna já existe
            result = db.session.execute(text("""
                SELECT COUNT(*) as count
                FROM pragma_table_info('configuracao_agendamento')
                WHERE name = 'intervalo_entrada'
            """))
            
            column_exists = result.fetchone()[0] > 0
            
            if column_exists:
                print("✓ Coluna 'intervalo_entrada' já existe na tabela 'configuracao_agendamento'")
                return True
            
            # Adicionar a coluna
            print("Adicionando coluna 'intervalo_entrada' à tabela 'configuracao_agendamento'...")
            db.session.execute(text("""
                ALTER TABLE configuracao_agendamento 
                ADD COLUMN intervalo_entrada INTEGER NOT NULL DEFAULT 15
            """))
            
            db.session.commit()
            print("✓ Coluna 'intervalo_entrada' adicionada com sucesso!")
            print("  - Valor padrão: 15 minutos")
            print("  - Todas as configurações existentes foram atualizadas")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro ao adicionar coluna: {str(e)}")
            return False

if __name__ == '__main__':
    print("=== Migração: Adicionar coluna intervalo_entrada ===")
    print()
    
    success = add_intervalo_entrada_column()
    
    if success:
        print()
        print("✓ Migração concluída com sucesso!")
        print("  A nova funcionalidade de intervalo de entrada está disponível.")
    else:
        print()
        print("✗ Migração falhou!")
        print("  Verifique os logs de erro acima.")
        sys.exit(1)