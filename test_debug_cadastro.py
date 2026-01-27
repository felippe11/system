import requests
import re
from bs4 import BeautifulSoup

print("=== TESTE DE DEBUG DO CADASTRO ===")

# Configuração
base_url = "http://localhost:5000"
email = "andre@teste.com"  # Usuário que existe no banco
senha = "123456"

# Sessão para manter cookies
session = requests.Session()

print("\n1. Fazendo login...")
# GET da página de login
login_response = session.get(f"{base_url}/login")
print(f"Login GET status: {login_response.status_code}")

# Extrair token CSRF
soup = BeautifulSoup(login_response.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
print(f"Token CSRF de login: {csrf_token[:20]}...")

# POST do login
login_data = {
    'email': email,
    'senha': senha,
    'csrf_token': csrf_token
}

login_post = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
print(f"Login POST status: {login_post.status_code}")
print(f"Headers de resposta: {dict(login_post.headers)}")

if login_post.status_code == 302:
    redirect_url = login_post.headers.get('Location', '')
    print(f"✅ Login bem-sucedido! Redirecionando para: {redirect_url}")
else:
    print("❌ Login falhou!")
    print(f"Conteúdo da resposta: {login_post.text[:500]}")
    exit(1)

print("\n2. Acessando página de cadastro...")
# Seguir o redirecionamento e depois ir para a página de cadastro
cadastro_response = session.get(f"{base_url}/trabalhos/novo")
print(f"Cadastro GET status: {cadastro_response.status_code}")

if cadastro_response.status_code != 200:
    print("❌ Erro ao acessar página de cadastro!")
    print(f"Conteúdo: {cadastro_response.text[:500]}")
    exit(1)

print("\n3. Analisando formulário...")
soup = BeautifulSoup(cadastro_response.text, 'html.parser')

# Verificar se há eventos disponíveis
eventos_select = soup.find('select', {'name': 'evento_id'})
if not eventos_select:
    print("❌ Campo de seleção de evento não encontrado!")
    exit(1)

eventos_options = eventos_select.find_all('option')
print(f"Eventos disponíveis: {len(eventos_options)}")

evento_id = None
for option in eventos_options:
    if option.get('value') and option.get('value') != '':
        evento_id = option.get('value')
        print(f"  - Evento ID: {evento_id}, Nome: {option.text.strip()}")
        break

if not evento_id:
    print("❌ Nenhum evento válido encontrado!")
    exit(1)

# Extrair token CSRF do formulário
csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
print(f"Token CSRF do formulário: {csrf_token[:20]}...")

# Verificar campos dinâmicos
campos_dinamicos = soup.find_all('div', class_='campo-dinamico')
print(f"Campos dinâmicos encontrados: {len(campos_dinamicos)}")

form_data = {
    'evento_id': evento_id,
    'csrf_token': csrf_token
}

# Preencher campos obrigatórios
for campo_div in campos_dinamicos:
    campo_input = campo_div.find(['input', 'select', 'textarea'])
    if campo_input:
        campo_nome = campo_input.get('name', '')
        campo_required = campo_input.get('required') is not None
        campo_tipo = campo_input.get('type', campo_input.name)
        
        print(f"  - Campo: {campo_nome}, Tipo: {campo_tipo}, Obrigatório: {campo_required}")
        
        if campo_required:
            if campo_tipo == 'text' or campo_tipo == 'textarea':
                if 'titulo' in campo_nome.lower() or 'título' in campo_nome.lower():
                    form_data[campo_nome] = "Trabalho de Teste - Debug"
                elif 'resumo' in campo_nome.lower():
                    form_data[campo_nome] = "Este é um resumo de teste para debug do sistema."
                else:
                    form_data[campo_nome] = f"Valor de teste para {campo_nome}"
            elif campo_tipo == 'select':
                options = campo_input.find_all('option')
                for option in options:
                    if option.get('value') and option.get('value') != '':
                        form_data[campo_nome] = option.get('value')
                        break
            elif campo_tipo == 'url':
                form_data[campo_nome] = "https://exemplo.com"

print(f"\nDados do formulário a serem enviados:")
for key, value in form_data.items():
    print(f"  {key}: {value}")

print("\n4. Enviando dados...")
submit_response = session.post(f"{base_url}/trabalhos/novo", data=form_data, allow_redirects=False)
print(f"Submit status: {submit_response.status_code}")
print(f"Headers de resposta: {dict(submit_response.headers)}")

if submit_response.status_code == 302:
    redirect_url = submit_response.headers.get('Location', '')
    print(f"✅ Redirecionamento após envio: {redirect_url}")
    
    # Seguir o redirecionamento para ver o resultado
    final_response = session.get(redirect_url)
    print(f"Página final status: {final_response.status_code}")
    
    # Verificar se há mensagens de sucesso ou erro
    soup_final = BeautifulSoup(final_response.text, 'html.parser')
    alerts = soup_final.find_all(['div'], class_=['alert', 'flash-message', 'error', 'success'])
    
    if alerts:
        print("\nMensagens encontradas:")
        for alert in alerts:
            print(f"  - {alert.get_text().strip()}")
    else:
        print("\nNenhuma mensagem de feedback encontrada.")
        
else:
    print("❌ Erro no envio do formulário!")
    print(f"Conteúdo da resposta: {submit_response.text[:1000]}")
    
    # Verificar se há erros específicos na resposta
    soup_error = BeautifulSoup(submit_response.text, 'html.parser')
    error_divs = soup_error.find_all(['div'], class_=['alert-danger', 'error', 'flash-error'])
    
    if error_divs:
        print("\nErros encontrados:")
        for error in error_divs:
            print(f"  - {error.get_text().strip()}")

print("\n=== FIM DO TESTE ===")