#!/usr/bin/env python3
"""
Script para tornar os campos nome e email obrigatórios na tabela revisor_candidatura.
Este script deve ser executado uma vez para atualizar o banco de dados existente.
"""

import sys
import os

# Adicionar o diretório raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

def update_revisor_candidatura_required_fields():
    """Torna os campos nome e email obrigatórios na tabela revisor_candidatura."""
    app = create_app()
    
    with app.app_context():
        try:
            # Primeiro, verificar se existem registros com nome ou email nulos
            result = db.session.execute(text("""
                SELECT COUNT(*) as count
                FROM revisor_candidatura
                WHERE nome IS NULL OR email IS NULL
            """))
            
            null_records = result.fetchone()[0]
            
            if null_records > 0:
                print(f"⚠️  Encontrados {null_records} registros com nome ou email nulos.")
                print("   Atualizando registros com valores padrão...")
                
                # Atualizar registros nulos com valores padrão
                db.session.execute(text("""
                    UPDATE revisor_candidatura 
                    SET nome = 'Nome não informado' 
                    WHERE nome IS NULL
                """))
                
                db.session.execute(text("""
                    UPDATE revisor_candidatura 
                    SET email = 'email_nao_informado_' || id || '@temp.com' 
                    WHERE email IS NULL
                """))
                
                db.session.commit()
                print("✓ Registros nulos atualizados com valores padrão.")
            
            # Verificar se as colunas já são NOT NULL
            result = db.session.execute(text("""
                SELECT sql FROM sqlite_master 
                WHERE type='table' AND name='revisor_candidatura'
            """))
            
            table_sql = result.fetchone()[0]
            
            if 'nome TEXT NOT NULL' in table_sql and 'email TEXT NOT NULL' in table_sql:
                print("✓ Os campos 'nome' e 'email' já são obrigatórios na tabela 'revisor_candidatura'")
                return True
            
            print("Atualizando estrutura da tabela para tornar nome e email obrigatórios...")
            
            # SQLite não suporta ALTER COLUMN diretamente, então precisamos recriar a tabela
            # Primeiro, criar uma tabela temporária com a nova estrutura
            db.session.execute(text("""
                CREATE TABLE revisor_candidatura_new (
                    id INTEGER PRIMARY KEY,
                    process_id INTEGER NOT NULL,
                    respostas TEXT,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL,
                    codigo TEXT UNIQUE,
                    etapa_atual INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pendente',
                    created_at DATETIME,
                    FOREIGN KEY (process_id) REFERENCES revisor_process (id)
                )
            """))
            
            # Copiar dados da tabela original para a nova
            db.session.execute(text("""
                INSERT INTO revisor_candidatura_new 
                (id, process_id, respostas, nome, email, codigo, etapa_atual, status, created_at)
                SELECT id, process_id, respostas, nome, email, codigo, etapa_atual, status, created_at
                FROM revisor_candidatura
            """))
            
            # Remover a tabela original
            db.session.execute(text("DROP TABLE revisor_candidatura"))
            
            # Renomear a nova tabela
            db.session.execute(text("""
                ALTER TABLE revisor_candidatura_new 
                RENAME TO revisor_candidatura
            """))
            
            db.session.commit()
            print("✓ Campos 'nome' e 'email' agora são obrigatórios!")
            print("  - Todos os registros existentes foram preservados")
            print("  - Novos cadastros exigirão nome e email")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro ao atualizar tabela: {str(e)}")
            return False

if __name__ == '__main__':
    print("=== Migração: Tornar nome e email obrigatórios em revisor_candidatura ===")
    print()
    
    success = update_revisor_candidatura_required_fields()
    
    if success:
        print()
        print("✓ Migração concluída com sucesso!")
        print("  Os campos nome e email agora são obrigatórios no cadastro de revisores.")
    else:
        print()
        print("✗ Migração falhou!")
        print("  Verifique os logs de erro acima.")
        sys.exit(1)