from app import create_app
from extensions import db
from models.user import Usuario
from models.event import Evento
from flask_login import login_user
from services import certificado_service

app = create_app()

with app.app_context():
    # Find a user of type 'participante'
    usuario = Usuario.query.filter_by(tipo='participante').first()
    if not usuario:
        print("No participante user found.")
        # Create a dummy user if none exists
        usuario = Usuario(nome="Test User", email="test@example.com", tipo="participante")
        usuario.set_password("password")
        db.session.add(usuario)
        db.session.commit()
    
    print(f"Using user: {usuario.email} (ID: {usuario.id})")

    # Mock request context and login
    with app.test_request_context('/meus_certificados'):
        login_user(usuario)
        
        try:
            from routes.participante_routes import meus_certificados
            response = meus_certificados()
            print("Route executed successfully.")
        except Exception as e:
            print(f"Caught exception: {e}")
            import traceback
            traceback.print_exc()
