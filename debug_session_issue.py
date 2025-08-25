from app import create_app
from models.user import Usuario, Cliente, Ministrante
from flask import session
from flask_login import login_user, current_user
import requests

app = create_app()

with app.test_client() as client:
    with app.app_context():
        print("=== Debug da Sessão ===\n")
        
        # 1. Verificar usuário
        user = Usuario.query.filter_by(email='andre@teste.com').first()
        if not user:
            user = Cliente.query.filter_by(email='andre@teste.com').first()
        
        print(f"1. Usuário encontrado: {user.nome} (ID: {user.id}, Tipo: {'cliente' if isinstance(user, Cliente) else 'usuario'})")
        
        # 2. Obter CSRF token primeiro
        print("\n2. Obtendo CSRF token...")
        response = client.get('/login')
        csrf_token = None
        if b'csrf_token' in response.data:
            import re
            match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)
            if match:
                csrf_token = match.group(1).decode('utf-8')
                print(f"  - CSRF token obtido: {csrf_token[:20]}...")
        
        # 3. Fazer login via POST com CSRF
        print("\n3. Fazendo login via POST...")
        login_data = {
            'email': 'andre@teste.com',
            'senha': '123456'
        }
        if csrf_token:
            login_data['csrf_token'] = csrf_token
            
        response = client.post('/login', data=login_data, follow_redirects=False)
        
        print(f"  - Status: {response.status_code}")
        print(f"  - Location: {response.headers.get('Location', 'N/A')}")
        
        # 4. Verificar se há Set-Cookie headers
        print("\n4. Verificando Set-Cookie headers...")
        set_cookies = response.headers.getlist('Set-Cookie')
        for cookie in set_cookies:
            print(f"  - {cookie[:100]}...")
        
        # 5. Tentar acessar dashboard
        print("\n5. Tentando acessar dashboard...")
        response = client.get('/dashboard', follow_redirects=False)
        print(f"  - Status: {response.status_code}")
        print(f"  - Location: {response.headers.get('Location', 'N/A')}")
        
        # 6. Verificar se há redirecionamento para login
        if response.status_code == 302 and '/login' in response.headers.get('Location', ''):
            print("  ❌ Redirecionado para login - sessão não mantida")
        else:
            print("  ✓ Acesso ao dashboard bem-sucedido")
        
        # 7. Tentar login manual dentro do contexto
        print("\n7. Testando login manual no contexto...")
        with client.session_transaction() as sess:
            sess['user_type'] = 'cliente' if isinstance(user, Cliente) else 'usuario'
            print(f"  - user_type definido na sessão: {sess['user_type']}")
        
        # Simular login_user
        login_user(user)
        print(f"  - current_user.is_authenticated: {current_user.is_authenticated}")
        print(f"  - current_user.id: {current_user.id if current_user.is_authenticated else 'N/A'}")
        
        # 8. Testar acesso após login manual
        print("\n8. Testando acesso após login manual...")
        response = client.get('/dashboard', follow_redirects=False)
        print(f"  - Status: {response.status_code}")
        print(f"  - Location: {response.headers.get('Location', 'N/A')}")
        
print("\n=== Debug concluído ===")