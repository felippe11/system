import os
import logging
from flask import Flask, url_for, request
import sys

# Logger do módulo
logger = logging.getLogger(__name__)

# Criar uma aplicação Flask simples para testar a geração de URLs
app = Flask(__name__)

# Importar a função external_url
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from utils import external_url
    logger.info("Função external_url importada com sucesso")
except ImportError as e:
    logger.error(f"Erro ao importar external_url: {e}")
    sys.exit(1)

@app.route('/test')
def test():
    return "Test route"

@app.route('/mercadopago/webhook', methods=['GET', 'POST'])
def webhook():
    return "Webhook route"

@app.route('/mercadopago/pagamento_sucesso')
def pagamento_sucesso():
    return "Sucesso route"

# Contexto de teste
with app.test_request_context():
    # Definir APP_BASE_URL para teste
    os.environ["APP_BASE_URL"] = "sistema.evento.com"
    
    try:
        # Gerar URLs para teste
        webhook_url = external_url('webhook')
        success_url = external_url('pagamento_sucesso')
        
        # Log das URLs geradas
        print(f"URL do webhook: {webhook_url}")
        print(f"URL de sucesso: {success_url}")
        
        # Verificar se as URLs são válidas
        for name, url in [("webhook", webhook_url), ("success", success_url)]:
            if not url.startswith(('http://', 'https://')):
                print(f"ERRO: URL de {name} não é absoluta: {url}")
            else:
                print(f"OK: URL de {name} é válida: {url}")
    
    except Exception as e:
        print(f"Erro ao gerar URLs: {e}")

if __name__ == "__main__":
    print("\nScript de teste para validar URLs do Mercado Pago")
    print("================================================")
    
    # Teste com configuração de ambiente
    print("\nTestando com APP_BASE_URL definido:")
    os.environ["APP_BASE_URL"] = "sistema.evento.com"
    with app.test_request_context():
        try:
            print(f"APP_BASE_URL = {os.environ.get('APP_BASE_URL')}")
            webhook_url = url_for('webhook', _external=True)
            print(f"url_for com _external=True: {webhook_url}")
            
            # Testar nossa função external_url
            webhook_url2 = external_url('webhook')
            print(f"external_url: {webhook_url2}")
        except Exception as e:
            print(f"Erro: {e}")
    
    # Teste sem configuração de ambiente
    print("\nTestando sem APP_BASE_URL:")
    os.environ.pop("APP_BASE_URL", None)
    with app.test_request_context():
        try:
            print(f"APP_BASE_URL = {os.environ.get('APP_BASE_URL')}")
            webhook_url = url_for('webhook', _external=True)
            print(f"url_for com _external=True: {webhook_url}")
            
            # Testar nossa função external_url
            webhook_url2 = external_url('webhook')
            print(f"external_url: {webhook_url2}")
        except Exception as e:
            print(f"Erro: {e}")
