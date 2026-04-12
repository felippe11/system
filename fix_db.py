import sys
from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE configuracao ADD COLUMN senha_feedback_aberto_hash VARCHAR(255);"))
        db.session.commit()
        print("Coluna senha_feedback_aberto_hash adicionada com sucesso.")
    except Exception as e:
        print("Erro (se a coluna já existir, ignore):", getattr(e, 'orig', e))
        db.session.rollback()
