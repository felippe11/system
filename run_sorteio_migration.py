"""
Script para executar a migração da tabela sorteio_ganhadores
"""
import psycopg2
from config import Config
from urllib.parse import urlparse

def run_migration():
    """Executa a migração SQL para criar a tabela sorteio_ganhadores"""
    conn = None
    try:
        # Parse a URI do SQLAlchemy
        uri = Config.SQLALCHEMY_DATABASE_URI
        # Remove o prefixo postgresql+psycopg2://
        if uri.startswith('postgresql+psycopg2://'):
            uri = uri.replace('postgresql+psycopg2://', 'postgresql://')
        
        result = urlparse(uri)
        
        # Conectar ao banco de dados
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        cur = conn.cursor()
        
        # Ler o arquivo SQL
        with open('migrations/add_sorteio_ganhadores_table.sql', 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # Executar SQL
        cur.execute(sql)
        conn.commit()
        
        print("✅ Migração executada com sucesso!")
        print("✅ Tabela sorteio_ganhadores criada")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao executar migração: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    run_migration()

