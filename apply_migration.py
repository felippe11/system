# -*- coding: utf-8 -*-

import os
import sys
from flask import Flask
from flask_migrate import Migrate, upgrade

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from extensions import db
    
    # Criar a aplicação
    app = create_app()
    
    # Configurar Flask-Migrate
    migrate_instance = Migrate(app, db)
    
    with app.app_context():
        # Aplicar migrações pendentes
        print("Aplicando migrações pendentes...")
        upgrade()
        print("Migrações aplicadas com sucesso!")
        
except Exception as e:
    print(f"Erro ao aplicar migrações: {e}")
    import traceback
    traceback.print_exc()