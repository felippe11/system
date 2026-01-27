from app import create_app
from models import Usuario
from flask import session
from bs4 import BeautifulSoup
import re

app = create_app()

with app.test_client() as client:
    # Primeiro fazer login
    login_response = client.get('/login')
    print(f'Login GET Status: {login_response.status_code}')
    
    # Extrair token CSRF do login
    login_html = login_response.get_data(as_text=True)
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', login_html)
    
    if csrf_match:
        csrf_token = csrf_match.group(1)
        print(f'Login CSRF Token encontrado: {csrf_token[:20]}...')
        
        # Fazer login
        login_post = client.post('/login', data={
            'csrf_token': csrf_token,
            'email': 'andre@teste.com',
            'senha': '123456'
        }, follow_redirects=False)
        
        print(f'Login POST Status: {login_post.status_code}')
        print(f'Login Headers: {dict(login_post.headers)}')
        
        # Agora tentar acessar a página de cadastro
        get_response = client.get('/trabalhos/novo')
        print(f'Cadastro GET Status: {get_response.status_code}')
        
        if get_response.status_code == 200:
            # Extrair token CSRF da página de cadastro
            html_content = get_response.get_data(as_text=True)
            csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', html_content)
            
            if csrf_match:
                csrf_token = csrf_match.group(1)
                print(f'Cadastro CSRF Token encontrado: {csrf_token[:20]}...')
                
                # Fazer POST do cadastro
                response = client.post('/trabalhos/novo', data={
                    'csrf_token': csrf_token,
                    'evento_id': 12,
                    'campo_1': 'Teste de Titulo',
                    'campo_2': 'Teste de Resumo'
                }, follow_redirects=True)
                
                print(f'Cadastro POST Status: {response.status_code}')
                print(f'Response: {response.get_data(as_text=True)[:1000]}')
            else:
                print('Token CSRF não encontrado na página de cadastro')
                print(f'HTML snippet: {html_content[:500]}')
        else:
            print(f'Erro ao acessar página de cadastro: {get_response.status_code}')
            print(f'Response: {get_response.get_data(as_text=True)[:500]}')
    else:
        print('Token CSRF não encontrado na página de login')
        print(f'Login HTML snippet: {login_html[:500]}')