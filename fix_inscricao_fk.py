# -*- coding: utf-8 -*-
import os
import sys
from sqlalchemy import text

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_constraint():
    try:
        from app import app
        from extensions import db
        
        with app.app_context():
            print("Iniciando correção de constraint na tabela inscricao...")
            
            # Tenta remover a constraint de chave estrangeira
            try:
                # O nome da constraint no erro é "inscricao_tipo_inscricao_id_fkey"
                sql = text('ALTER TABLE inscricao DROP CONSTRAINT IF EXISTS "inscricao_tipo_inscricao_id_fkey"')
                db.engine.execute(sql)
                print("Constraint 'inscricao_tipo_inscricao_id_fkey' removida com sucesso!")
            except Exception as e:
                print(f"Erro ao tentar remover constraint: {e}")

            print("Correção concluída.")
            
    except ImportError as e:
        print(f"Erro de importação: {e}")
        print("Certifique-se de executar este script na raiz do projeto.")
    except Exception as e:
        print(f"Erro inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_constraint()
