import os
import sys
import sqlite3
import psycopg2
from urllib.parse import urlparse

# Adicionar o diretorio raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def add_pode_aprovar_compras_field():
    """Adiciona o campo pode_aprovar_compras a tabela usuario."""
    
    # Verificar se eh SQLite ou PostgreSQL
    db_url = os.getenv('DATABASE_URL', 'sqlite:///instance/database.db')
    
    try:
        if db_url.startswith('sqlite'):
            # SQLite
            db_path = db_url.replace('sqlite:///', '')
            if not os.path.exists(db_path):
                print(f"Banco SQLite nao encontrado: {db_path}")
                return False
                
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar se a coluna ja existe
            cursor.execute("PRAGMA table_info(usuario)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'pode_aprovar_compras' in columns:
                print("Campo pode_aprovar_compras ja existe na tabela usuario")
                conn.close()
                return True
            
            # Adicionar a coluna
            cursor.execute("ALTER TABLE usuario ADD COLUMN pode_aprovar_compras BOOLEAN DEFAULT 0")
            
            # Atualizar usuarios admin
            cursor.execute("UPDATE usuario SET pode_aprovar_compras = 1 WHERE tipo = 'admin'")
            
            conn.commit()
            conn.close()
            
            print("Campo pode_aprovar_compras adicionado com sucesso")
            return True
            
        else:
            # PostgreSQL
            parsed = urlparse(db_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                port=parsed.port
            )
            cursor = conn.cursor()
            
            # Verificar se a coluna ja existe
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'usuario' AND column_name = 'pode_aprovar_compras'
            """)
            
            if cursor.fetchone():
                print("Campo pode_aprovar_compras ja existe na tabela usuario")
                conn.close()
                return True
            
            # Adicionar a coluna
            cursor.execute("ALTER TABLE usuario ADD COLUMN pode_aprovar_compras BOOLEAN DEFAULT FALSE")
            
            # Atualizar usuarios admin
            cursor.execute("UPDATE usuario SET pode_aprovar_compras = TRUE WHERE tipo = 'admin'")
            
            conn.commit()
            conn.close()
            
            print("Campo pode_aprovar_compras adicionado com sucesso")
            return True
            
    except Exception as e:
        print(f"Erro ao adicionar campo: {e}")
        return False

if __name__ == '__main__':
    add_pode_aprovar_compras_field()