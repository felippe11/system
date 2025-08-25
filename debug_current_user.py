import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.user import Usuario, Cliente
from flask import session
from flask_login import login_user, current_user

app = create_app()

with app.app_context():
    with app.test_client() as client:
        print("=== Debug Current User ===\n")
        
        # 1. Obter CSRF token
        print("1. Obtendo CSRF token...")
        response = client.get('/login')
        csrf_token = None
        if response.status_code == 200:
            import re
            csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
            if csrf_match:
                csrf_token = csrf_match.group(1)
                print(f"  - CSRF token obtido: {csrf_token[:20]}...")
        
        # 2. Fazer login
        print("\n2. Fazendo login...")
        login_data = {
            'email': 'andre@teste.com',
            'senha': '123456'
        }
        if csrf_token:
            login_data['csrf_token'] = csrf_token
            
        response = client.post('/login', data=login_data, follow_redirects=False)
        
        print(f"  - Status: {response.status_code}")
        print(f"  - Location: {response.headers.get('Location', 'N/A')}")
        
        # 3. Verificar sessão
        with client.session_transaction() as sess:
            print(f"\n3. Informações da sessão:")
            print(f"  - user_type: {sess.get('user_type', 'N/A')}")
            print(f"  - _user_id: {sess.get('_user_id', 'N/A')}")
        
        # 4. Testar rota get_eventos_cliente
        print(f"\n4. Testando rota get_eventos_cliente...")
        response = client.get('/get_eventos_cliente')
        print(f"  - Status: {response.status_code}")
        print(f"  - Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            try:
                data = response.get_json()
                print(f"  - JSON: {data}")
                print(f"  - Eventos encontrados: {len(data.get('eventos', []))}")
            except Exception as e:
                print(f"  - Erro ao processar JSON: {e}")
                print(f"  - Conteúdo: {response.get_data(as_text=True)}")
        else:
            print(f"  - Conteúdo: {response.get_data(as_text=True)}")
        
print("\n=== Debug concluído ===")