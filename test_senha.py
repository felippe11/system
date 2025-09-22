from app import create_app
from models import Usuario
from werkzeug.security import check_password_hash

app = create_app()
app.app_context().push()

user = Usuario.query.filter_by(email='andre@teste.com').first()
if user:
    print(f'Usuario: {user.nome}')
    print(f'Email: {user.email}')
    print(f'Tipo: {user.tipo}')
    print(f'Senha correta com "senha123": {check_password_hash(user.senha, "senha123")}')
    print(f'Senha correta com "123456": {check_password_hash(user.senha, "123456")}')
    print(f'Senha correta com "andre123": {check_password_hash(user.senha, "andre123")}')
else:
    print('Usuario não encontrado')