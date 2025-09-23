#!/usr/bin/env python3
"""
Script para atualizar os status dos processos seletivos existentes
de 'ativo' para 'aberto' para padronizar o sistema.
"""

from app import create_app
from models.review import RevisorProcess
from extensions import db

def update_process_status():
    """Atualiza os status dos processos de 'ativo' para 'aberto'."""
    app = create_app()
    
    with app.app_context():
        # Buscar todos os processos com status 'ativo'
        processos_ativos = RevisorProcess.query.filter_by(status='ativo').all()
        
        print(f"Encontrados {len(processos_ativos)} processos com status 'ativo'")
        
        if processos_ativos:
            # Atualizar para 'aberto'
            for processo in processos_ativos:
                processo.status = 'aberto'
                print(f"Atualizando processo ID {processo.id}: {processo.nome}")
            
            # Salvar as alterações
            db.session.commit()
            print(f"✅ {len(processos_ativos)} processos atualizados com sucesso!")
        else:
            print("Nenhum processo com status 'ativo' encontrado.")
        
        # Verificar se existem outros status que precisam ser atualizados
        outros_status = db.session.query(RevisorProcess.status).distinct().all()
        print("\nStatus encontrados no banco:")
        for status in outros_status:
            count = RevisorProcess.query.filter_by(status=status[0]).count()
            print(f"  - {status[0]}: {count} processos")

if __name__ == '__main__':
    update_process_status()