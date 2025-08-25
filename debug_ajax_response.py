import requests
from bs4 import BeautifulSoup
import json

# Criar uma sessão para manter cookies
session = requests.Session()

print("=== Debug da Resposta AJAX ===")

# 1. Login completo
login_page = session.get('http://localhost:5001/login')
soup = BeautifulSoup(login_page.content, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrf_token'})
csrf_value = csrf_token.get('value')

login_data = {
    'email': 'andre@teste.com',
    'senha': '123456',
    'csrf_token': csrf_value
}

login_response = session.post('http://localhost:5001/login', data=login_data)
print(f"Login status: {login_response.status_code}")
print(f"Login URL final: {login_response.url}")
print(f"Cookies após login: {session.cookies}")

# 2. Verificar se foi redirecionado para dashboard
if login_response.url != 'http://localhost:5001/login':
    print(f"✓ Redirecionado para: {login_response.url}")
else:
    print("✗ Ainda na página de login - login pode ter falhado")

# 3. Testar AJAX
ajax_response = session.get('http://localhost:5001/get_eventos_cliente')
print(f"\nAJAX status: {ajax_response.status_code}")
print(f"AJAX headers: {dict(ajax_response.headers)}")
print(f"AJAX content-type: {ajax_response.headers.get('content-type', 'N/A')}")

# Verificar se é JSON ou HTML
if 'application/json' in ajax_response.headers.get('content-type', ''):
    print("✓ Resposta é JSON")
    try:
        data = ajax_response.json()
        print(f"Dados JSON: {data}")
    except:
        print("✗ Erro ao decodificar JSON")
else:
    print("✗ Resposta é HTML (provavelmente página de login)")
    # Verificar se contém formulário de login
    if 'type="password"' in ajax_response.text:
        print("  → Confirmado: é página de login")
    else:
        print(f"  → Conteúdo: {ajax_response.text[:200]}...")