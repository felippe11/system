# -*- coding: utf-8 -*-
"""
Script para inicializar o banco de dados
"""

import os
import sys

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db

def init_database():
    """Inicializa o banco de dados criando todas as tabelas"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Criando todas as tabelas...")
            db.create_all()
            print("Banco de dados inicializado com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao inicializar banco de dados: {e}")
            return False

if __name__ == "__main__":
    init_database()