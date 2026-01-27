#!/usr/bin/env python3
"""
Script para criar as tabelas do sistema de votação.
Execute este script para criar as tabelas necessárias no banco de dados.
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from config import Config
from extensions import db
from models.voting import (
    VotingEvent,
    VotingCategory, 
    VotingQuestion,
    VotingWork,
    VotingAssignment,
    VotingVote,
    VotingResponse,
    VotingResult,
    VotingAuditLog
)

def create_voting_tables():
    """Cria as tabelas do sistema de votação."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    with app.app_context():
        try:
            print("Criando tabelas do sistema de votação...")
            
            # Criar todas as tabelas
            db.create_all()
            
            print("✅ Tabelas criadas com sucesso!")
            print("\nTabelas criadas:")
            print("- voting_event")
            print("- voting_category") 
            print("- voting_question")
            print("- voting_work")
            print("- voting_assignment")
            print("- voting_vote")
            print("- voting_response")
            print("- voting_result")
            print("- voting_audit_log")
            
        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            return False
            
    return True

if __name__ == "__main__":
    success = create_voting_tables()
    if success:
        print("\n🎉 Sistema de votação configurado com sucesso!")
    else:
        print("\n💥 Falha na configuração do sistema de votação.")
        sys.exit(1)

