import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.user import Usuario
from werkzeug.security import check_password_hash
from flask_sqlalchemy import SQLAlchemy

app = create_app()

with app.app_context():
    print("=== Verificação do Processo de Login ===")
    
    # 1. Verificar se o usuário existe
    email = "andre@teste.com"
    user = Usuario.query.filter_by(email=email).first()
    
    if not user:
        print(f"❌ Usuário {email} não encontrado")
        exit(1)
    
    print(f"✓ Usuário encontrado: {user.nome} ({user.email})")
    print(f"  - ID: {user.id}")
    print(f"  - Tipo: {user.tipo}")
    print(f"  - Ativo: {getattr(user, 'ativo', 'N/A')}")
    
    # 2. Verificar a senha
    senha_teste = "123456"
    print(f"\n2. Verificando senha...")
    print(f"  - Senha hash no banco: {user.senha[:50]}...")
    
    # Verificar se a senha está correta
    if check_password_hash(user.senha, senha_teste):
        print(f"✓ Senha '{senha_teste}' está correta")
    else:
        print(f"❌ Senha '{senha_teste}' está incorreta")
        
        # Tentar outras senhas comuns
        senhas_teste = ["123", "teste", "admin", "password"]
        for senha in senhas_teste:
            if check_password_hash(user.senha, senha):
                print(f"✓ Senha correta encontrada: '{senha}'")
                break
        else:
            print("❌ Nenhuma senha comum funcionou")
    
    # 3. Verificar se há campos obrigatórios faltando
    print(f"\n3. Verificando campos do usuário...")
    campos_importantes = ['nome', 'email', 'tipo', 'cpf']
    for campo in campos_importantes:
        valor = getattr(user, campo, None)
        if valor:
            print(f"  ✓ {campo}: {valor}")
        else:
            print(f"  ❌ {campo}: VAZIO")
    
    # 4. Verificar se há outros usuários do mesmo tipo
    print(f"\n4. Verificando outros usuários do tipo 'cliente'...")
    clientes = Usuario.query.filter_by(tipo='cliente').all()
    print(f"Total de clientes: {len(clientes)}")
    for cliente in clientes:
        print(f"  - {cliente.nome} ({cliente.email}) - ID: {cliente.id}")
    
    print("\n=== Verificação concluída ===")