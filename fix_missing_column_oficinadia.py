from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        print("Verificando e adicionando coluna 'ordem_exibicao' na tabela 'oficinadia'...")
        # Usando IF NOT EXISTS para evitar erro se ja existir (PostgreSQL 9.6+)
        db.session.execute(text("ALTER TABLE oficinadia ADD COLUMN IF NOT EXISTS ordem_exibicao INTEGER DEFAULT 0;"))
        db.session.commit()
        print("Sucesso! Coluna verificada/adicionada.")
    except Exception as e:
        print(f"Erro ao adicionar coluna: {e}")
        db.session.rollback()
