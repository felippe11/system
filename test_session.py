from app import create_app
from models.user import Usuario
from flask_login import current_user
from flask import session

app = create_app()
with app.app_context():
    with app.test_request_context():
        print(f"Current user authenticated: {current_user.is_authenticated}")
        print(f"Current user: {current_user}")
        print(f"Session: {dict(session)}")
        
        # Verificar se há usuários revisores no sistema
        revisores = Usuario.query.filter_by(tipo='revisor').all()
        print(f"\nRevisores no sistema: {len(revisores)}")
        for revisor in revisores:
            print(f"- {revisor.nome} ({revisor.email}) - ID: {revisor.id}")