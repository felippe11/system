from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        print("Verificando e adicionando coluna 'tipos_inscricao_permitidos' na tabela 'oficina'...")
        # Usando IF NOT EXISTS para evitar erro se ja existir (PostgreSQL 9.6+)
        db.session.execute(text("ALTER TABLE oficina ADD COLUMN IF NOT EXISTS tipos_inscricao_permitidos TEXT;"))
        db.session.commit()
        print("Sucesso! Coluna verificada/adicionada.")
    except Exception as e:
        print(f"Erro ao adicionar coluna: {e}")
        db.session.rollback()
