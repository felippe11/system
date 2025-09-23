import requests
import re
from bs4 import BeautifulSoup

print("=== TESTE DETALHADO DE CADASTRO DE TRABALHO ===")

# URL base
base_url = "http://localhost:5000"
login_url = f"{base_url}/login"
cadastro_url = f"{base_url}/trabalhos/novo"

# Criar sessão
session = requests.Session()

print("\n1. Fazendo login...")

# Obter página de login
login_page = session.get(login_url)
print(f"Status da página de login: {login_page.status_code}")

# Extrair CSRF token da página de login
soup = BeautifulSoup(login_page.content, 'html.parser')
csrf_input = soup.find('input', {'name': 'csrf_token'})
if not csrf_input:
    print("❌ CSRF token não encontrado na página de login!")
    exit(1)

csrf_token = csrf_input.get('value')
print(f"CSRF token obtido: {csrf_token[:20]}...")

# Dados de login
login_data = {
    'email': 'andre@teste.com',
    'senha': '123456',
    'csrf_token': csrf_token
}

# Fazer login
login_response = session.post(login_url, data=login_data)
print(f"Status do login: {login_response.status_code}")

if login_response.status_code != 200:
    print(f"❌ Erro no login: {login_response.status_code}")
    exit(1)

# Verificar se login foi bem-sucedido
if 'login' in login_response.url:
    print("❌ Login falhou - ainda na página de login")
    print(f"URL atual: {login_response.url}")
    exit(1)

print("✅ Login realizado com sucesso!")

print("\n2. Acessando página de cadastro de trabalho...")

# Obter página de cadastro
cadastro_page = session.get(cadastro_url)
print(f"Status da página de cadastro: {cadastro_page.status_code}")

if cadastro_page.status_code != 200:
    print(f"❌ Erro ao acessar página de cadastro: {cadastro_page.status_code}")
    exit(1)

# Extrair CSRF token da página de cadastro
soup = BeautifulSoup(cadastro_page.content, 'html.parser')
csrf_input = soup.find('input', {'name': 'csrf_token'})
if not csrf_input:
    print("❌ CSRF token não encontrado na página de cadastro!")
    exit(1)

csrf_token = csrf_input.get('value')
print(f"CSRF token da página de cadastro: {csrf_token[:20]}...")

# Verificar se há campos do formulário
print("\n3. Analisando campos do formulário...")

# Buscar todos os campos de input
inputs = soup.find_all(['input', 'select', 'textarea'])
print(f"Campos encontrados: {len(inputs)}")

for inp in inputs:
    name = inp.get('name', 'sem_nome')
    input_type = inp.get('type', inp.name)
    required = 'required' in inp.attrs
    print(f"  - {name}: {input_type} {'(obrigatório)' if required else ''}")

print("\n4. Enviando dados do formulário...")

# Dados completos do formulário (usando os nomes corretos dos campos)
form_data = {
    'csrf_token': csrf_token,
    'evento_id': '12',
    'campo_16': 'Teste de Trabalho Automatizado',  # Título
    'campo_17': 'Prática Educacional',  # Categoria
    'campo_18': 'Rede Municipal de Teste',  # Rede de ensino
    'campo_19': 'Ensino Fundamental',  # Etapa de ensino
    'campo_20': 'https://exemplo.com/trabalho.pdf'  # URL do PDF
}

print("Dados a serem enviados:")
for key, value in form_data.items():
    if key != 'csrf_token':
        print(f"  {key}: {value}")
    else:
        print(f"  {key}: {value[:20]}...")

# Enviar formulário
submit_response = session.post(cadastro_url, data=form_data)
print(f"\nStatus da submissão: {submit_response.status_code}")
print(f"URL final: {submit_response.url}")

# Analisar resposta
if submit_response.status_code == 200:
    # Verificar se há mensagens de erro ou sucesso
    soup = BeautifulSoup(submit_response.content, 'html.parser')
    
    # Buscar mensagens de erro
    error_messages = soup.find_all(['div'], class_=['alert-danger', 'error', 'invalid-feedback'])
    if error_messages:
        print("\n❌ Mensagens de erro encontradas:")
        for msg in error_messages:
            print(f"  - {msg.get_text().strip()}")
    
    # Buscar mensagens de sucesso
    success_messages = soup.find_all(['div'], class_=['alert-success', 'success'])
    if success_messages:
        print("\n✅ Mensagens de sucesso encontradas:")
        for msg in success_messages:
            print(f"  - {msg.get_text().strip()}")
    
    # Verificar se ainda está na página de cadastro
    title = soup.find('title')
    if title and 'Adicionar Novo Trabalho' in title.get_text():
        print("\n⚠️ Ainda na página de cadastro - possível erro de validação")
        
        # Buscar campos com erros
        invalid_fields = soup.find_all(['input', 'select', 'textarea'], class_=['is-invalid'])
        if invalid_fields:
            print("Campos com erro:")
            for field in invalid_fields:
                name = field.get('name', 'sem_nome')
                print(f"  - {name}")
    else:
        print("\n✅ Redirecionado para outra página - possível sucesso")
        if title:
            print(f"Título da página: {title.get_text().strip()}")

else:
    print(f"\n❌ Erro HTTP: {submit_response.status_code}")
    print(f"Conteúdo: {submit_response.text[:500]}...")

print("\n=== FIM DO TESTE DETALHADO ===")