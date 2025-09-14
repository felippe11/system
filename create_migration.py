#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from flask import Flask
from flask_migrate import Migrate, init, migrate, upgrade

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db
    
    # Configurar Flask-Migrate
    migrate_instance = Migrate(app, db)
    
    with app.app_context():
        # Criar migração para os novos modelos
        print("Criando migração para MaterialDisponivel e SolicitacaoMaterialFormador...")
        migrate(message='Add MaterialDisponivel and SolicitacaoMaterialFormador models')
        print("Migração criada com sucesso!")
        
except Exception as e:
    print(f"Erro ao criar migração: {e}")
    import traceback
    traceback.print_exc()