from app import app, db
from models import Usuario
from werkzeug.security import generate_password_hash

with app.app_context():  # ✅ Criando um contexto da aplicação Flask
    # Verifica se o administrador já existe
    if not Usuario.query.filter_by(email="admin@email.com").first():
        # Criar o administrador
        admin = Usuario(
            nome="Administrador",
            cpf="00000000000",
            email="admin@email.com",
            senha=generate_password_hash("admin123"),
            formacao="Administrador",
            tipo="admin"
        )

        db.session.add(admin)
        db.session.commit()
        print("✅ Administrador criado com sucesso!")
    else:
        print("⚠️ O administrador já existe no banco de dados.")
