from app import app
from extensions import db
from sqlalchemy import text

with app.app_context():
    try:
        # Adicionar a coluna taxa_diferenciada à tabela configuracao_cliente
        db.session.execute(text("ALTER TABLE configuracao_cliente ADD COLUMN IF NOT EXISTS taxa_diferenciada NUMERIC(5,2);"))
        db.session.commit()
        print("Coluna taxa_diferenciada adicionada com sucesso à tabela configuracao_cliente!")
    except Exception as e:
        print(f"Erro ao adicionar coluna: {e}")
