import requests
from bs4 import BeautifulSoup

# Configuração
BASE_URL = "http://localhost:5001"
LOGIN_URL = f"{BASE_URL}/login"
DASHBOARD_URL = f"{BASE_URL}/dashboard"
CONTROL_URL = f"{BASE_URL}/submissoes/controle"

# Credenciais
EMAIL = "andre@teste.com"
SENHA = "123456"

def debug_session():
    session = requests.Session()
    
    print("=== Debug da Sessão ===")
    
    # 1. Login
    print("\n1. Fazendo login...")
    login_page = session.get(LOGIN_URL)
    soup = BeautifulSoup(login_page.content, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'}).get('value')
    
    login_data = {
        'email': EMAIL,
        'senha': SENHA,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(LOGIN_URL, data=login_data, allow_redirects=True)
    print(f"Status após login: {login_response.status_code}")
    print(f"URL final após login: {login_response.url}")
    
    # Verificar se chegou ao dashboard
    if 'dashboard' in login_response.url:
        print("✓ Login bem-sucedido - redirecionado para dashboard")
    elif 'login' in login_response.url:
        print("❌ Login falhou - ainda na página de login")
        return
    else:
        print(f"⚠️ Redirecionado para: {login_response.url}")
    
    # 2. Verificar cookies de sessão
    print("\n2. Verificando cookies de sessão...")
    for cookie in session.cookies:
        print(f"Cookie: {cookie.name} = {cookie.value[:20]}...")
    
    # 3. Tentar acessar dashboard diretamente
    print("\n3. Acessando dashboard...")
    dashboard_response = session.get(DASHBOARD_URL)
    print(f"Status dashboard: {dashboard_response.status_code}")
    print(f"URL dashboard: {dashboard_response.url}")
    
    if 'login' in dashboard_response.url:
        print("❌ Redirecionado para login ao acessar dashboard")
        return
    else:
        print("✓ Dashboard acessado com sucesso")
    
    # 4. Verificar se há informações do usuário na página
    if 'Andre Teste' in dashboard_response.text or 'andre@teste.com' in dashboard_response.text:
        print("✓ Informações do usuário encontradas no dashboard")
    else:
        print("⚠️ Informações do usuário não encontradas")
    
    # 5. Tentar acessar página de controle
    print("\n4. Acessando página de controle...")
    control_response = session.get(CONTROL_URL)
    print(f"Status controle: {control_response.status_code}")
    print(f"URL controle: {control_response.url}")
    
    if 'login' in control_response.url:
        print("❌ Redirecionado para login ao acessar controle")
        
        # Verificar se há mensagem de erro
        soup = BeautifulSoup(control_response.content, 'html.parser')
        alerts = soup.find_all('div', class_='alert')
        for alert in alerts:
            print(f"Mensagem de alerta: {alert.get_text().strip()}")
    else:
        print("✓ Página de controle acessada com sucesso")
        
        # Verificar se há conteúdo específico da página
        if 'Controle de Submissões' in control_response.text:
            print("✓ Conteúdo da página de controle carregado")
        else:
            print("⚠️ Conteúdo esperado não encontrado")
    
    print("\n=== Debug concluído ===")

if __name__ == "__main__":
    debug_session()