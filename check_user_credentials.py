#!/usr/bin/env python3
from app import create_app
from models.user import Usuario
from werkzeug.security import check_password_hash

def check_credentials():
    """Verificar as credenciais do usuário no banco"""
    app = create_app()
    
    with app.app_context():
        # Buscar usuário por email
        user = Usuario.query.filter_by(email='andre@teste.com').first()
        
        if user:
            print(f"Usuário encontrado:")
            print(f"  ID: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  Tipo: {user.tipo}")
            print(f"  Senha hash: {user.senha[:50]}...")
            
            # Testar senha
            senha_correta = check_password_hash(user.senha, '123456')
            print(f"  Senha '123456' está correta: {senha_correta}")
            
            # Testar outras senhas possíveis
            for senha_teste in ['123', 'andre', 'teste', 'admin']:
                if check_password_hash(user.senha, senha_teste):
                    print(f"  Senha correta encontrada: '{senha_teste}'")
                    break
            else:
                print("  Nenhuma senha comum funcionou")
                
        else:
            print("Usuário não encontrado com email 'andre@teste.com'")
            
            # Listar todos os usuários
            print("\nTodos os usuários no banco:")
            users = Usuario.query.all()
            for u in users:
                print(f"  ID: {u.id}, Email: {u.email}, Tipo: {u.tipo}")

if __name__ == "__main__":
    check_credentials()