import os
import logging
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()

# Logger do módulo
logger = logging.getLogger(__name__)

# Tentar importar o módulo mercadopago
try:
    import mercadopago
    logger.info("Módulo mercadopago importado com sucesso")
except ImportError as e:
    logger.error(f"Erro ao importar mercadopago: {e}")
    print("\nO módulo mercadopago não está instalado.")
    print("Por favor, instale-o usando: pip install mercadopago")
    sys.exit(1)

def test_mercadopago_sdk():
    """Testar a conexão com o Mercado Pago usando o SDK."""
    print("\nTeste do SDK do Mercado Pago")
    print("===========================")
    
    # Verificar se o token está configurado
    token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not token:
        print("ERRO: MERCADOPAGO_ACCESS_TOKEN não está definido no ambiente.")
        print("Configure-o no arquivo .env ou como variável de ambiente.")
        return False
    
    try:
        # Inicializar SDK
        print(f"Inicializando SDK com token {'*' * (len(token) - 8)}{token[-8:]}")
        sdk = mercadopago.SDK(token)
          # Testar uma requisição simples para verificar se o token é válido
        print("Testando acesso à API do Mercado Pago...")
        try:
            # Primeiro, tentar utilizando payment_methods()
            response = sdk.payment_methods().list_all()
        except Exception as e1:
            print(f"Tentando método alternativo... ({str(e1)})")
            # Se falhar, tentar com versão alternativa da API
            response = sdk.payment().search({"status": "approved"})
        
        if response["status"] == 200:
            print("SUCESSO: Conexão com o Mercado Pago estabelecida com sucesso!")
            print(f"Status: {response['status']}")
            print(f"Métodos de pagamento disponíveis: {len(response['response'])}")
            return True
        else:
            print(f"ERRO: Resposta inesperada do Mercado Pago. Status: {response['status']}")
            print(f"Resposta: {response}")
            return False
    
    except Exception as e:
        print(f"ERRO: Falha ao conectar com o Mercado Pago: {str(e)}")
        return False

def test_create_preference():
    """Testar a criação de uma preferência de pagamento."""
    print("\nTeste de criação de preferência de pagamento")
    print("==========================================")
    
    # Verificar se o token está configurado
    token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not token:
        print("ERRO: MERCADOPAGO_ACCESS_TOKEN não está definido no ambiente.")
        return False
    
    try:
        # Inicializar SDK
        sdk = mercadopago.SDK(token)
        
        # Configurar URLs
        base_url = os.getenv("APP_BASE_URL", "sistema.evento.com")
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"https://{base_url}"
        
        notification_url = f"{base_url}/mercadopago/webhook"
        success_url = f"{base_url}/mercadopago/sucesso"
        failure_url = f"{base_url}/mercadopago/falha"
        pending_url = f"{base_url}/mercadopago/pendente"
        
        # Dados da preferência
        preference_data = {
            "items": [
                {
                    "id": "test-item-1",
                    "title": "Inscrição de Teste",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": 10.0,
                }
            ],
            "payer": {"email": "teste@example.com", "name": "Usuario Teste"},
            "external_reference": "test-ref-1",
            "back_urls": {
                "success": success_url,
                "failure": failure_url,
                "pending": pending_url,
            },
            "notification_url": notification_url,
        }
        
        print("Criando preferência de pagamento com os seguintes dados:")
        print(f"- Item: {preference_data['items'][0]['title']}")
        print(f"- Preço: R$ {preference_data['items'][0]['unit_price']:.2f}")
        print(f"- URL de notificação: {notification_url}")
        print(f"- URL de sucesso: {success_url}")
        
        # Criar preferência
        response = sdk.preference().create(preference_data)
        
        if "response" in response:
            print("\nSUCESSO: Preferência criada!")
            print(f"ID da preferência: {response['response']['id']}")
            print(f"Link de pagamento: {response['response']['init_point']}")
            return True
        else:
            print("\nERRO: Falha ao criar preferência.")
            print(f"Resposta: {response}")
            return False
    
    except Exception as e:
        print(f"\nERRO: Exceção ao criar preferência: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Detalhes da resposta: {e.response}")
        return False

if __name__ == "__main__":
    print("\nTeste de integração com o Mercado Pago")
    print("====================================")
    
    # Verificar ambiente
    print("\nVariáveis de ambiente:")
    print(f"MERCADOPAGO_ACCESS_TOKEN definido: {'Sim' if os.getenv('MERCADOPAGO_ACCESS_TOKEN') else 'Não'}")
    print(f"APP_BASE_URL: {os.getenv('APP_BASE_URL', 'Não definido')}")
    
    # Executar testes
    if test_mercadopago_sdk():
        test_create_preference()
    
    print("\nFim dos testes.")
