#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.compra import NivelAprovacao, AprovacaoCompra

def create_tables():
    """Cria as tabelas de aprovação."""
    app = create_app()
    
    with app.app_context():
        try:
            # Criar as tabelas
            db.create_all()
            print("Tabelas de aprovação criadas com sucesso!")
            
            # Verificar se as tabelas foram criadas
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'nivel_aprovacao' in tables:
                print("✓ Tabela nivel_aprovacao criada")
            else:
                print("✗ Tabela nivel_aprovacao não encontrada")
                
            if 'aprovacao_compra' in tables:
                print("✓ Tabela aprovacao_compra criada")
            else:
                print("✗ Tabela aprovacao_compra não encontrada")
                
        except Exception as e:
            print("Erro ao criar tabelas: {}".format(e))
            return False
            
    return True

if __name__ == '__main__':
    create_tables()