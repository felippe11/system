# -*- coding: utf-8 -*-
"""
Script de migracao para criar as tabelas de orcamento e historico de alteracoes orcamentarias
"""

import os
import sys

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.orcamento import Orcamento, HistoricoOrcamento

def create_tables():
    """Cria as tabelas de orcamento e historico"""
    try:
        # Criar as tabelas
        db.create_all()
        
        print("Tabelas criadas com sucesso:")
        print("   - orcamento")
        print("   - historico_orcamento")
        
        return True
        
    except Exception as e:
        print("Erro ao criar tabelas: " + str(e))
        return False

def drop_tables():
    """Remove as tabelas de orcamento e historico (use com cuidado!)"""
    try:
        # Remover as tabelas
        HistoricoOrcamento.__table__.drop(db.engine, checkfirst=True)
        Orcamento.__table__.drop(db.engine, checkfirst=True)
        
        print("Tabelas removidas com sucesso:")
        print("   - orcamento")
        print("   - historico_orcamento")
        
        return True
        
    except Exception as e:
        print("Erro ao remover tabelas: " + str(e))
        return False

if __name__ == "__main__":
    app = create_app()
    
    with app.app_context():
        if len(sys.argv) > 1 and sys.argv[1] == "drop":
            print("ATENCAO: Voce esta prestes a remover as tabelas de orcamento!")
            confirm = input("Digite 'CONFIRMAR' para continuar: ")
            if confirm == "CONFIRMAR":
                drop_tables()
            else:
                print("Operacao cancelada.")
        else:
            create_tables()