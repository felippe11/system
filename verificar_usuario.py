import sys
sys.path.append('.')

from app import create_app
from extensions import db
from models.user import Usuario
from werkzeug.security import check_password_hash

print("=== VERIFICAÇÃO DO USUÁRIO ===")

app = create_app()
with app.app_context():
    # Buscar usuário
    usuario = Usuario.query.filter_by(email='andre@teste.com').first()
    
    if not usuario:
        print("❌ Usuário andre@teste.com não encontrado!")
        
        # Listar todos os usuários
        print("\nUsuários existentes:")
        usuarios = Usuario.query.all()
        for u in usuarios:
            print(f"  - ID: {u.id}, Email: {u.email}, Nome: {u.nome}")
    else:
        print(f"✅ Usuário encontrado:")
        print(f"  - ID: {usuario.id}")
        print(f"  - Email: {usuario.email}")
        print(f"  - Nome: {usuario.nome}")
        print(f"  - Ativo: {usuario.ativo}")
        print(f"  - Evento ID: {usuario.evento_id}")
        
        # Testar senhas comuns
        senhas_teste = ['123', '123456', 'andre', 'teste', 'admin']
        
        print("\nTestando senhas:")
        for senha in senhas_teste:
            if check_password_hash(usuario.senha, senha):
                print(f"✅ Senha correta: {senha}")
                break
            else:
                print(f"❌ Senha incorreta: {senha}")
        else:
            print("\n⚠️ Nenhuma das senhas testadas funcionou")
            print(f"Hash da senha: {usuario.senha[:50]}...")

print("\n=== FIM DA VERIFICAÇÃO ===")