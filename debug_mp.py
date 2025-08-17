import os
import logging
import json
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()

# Logger deste módulo
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

def test_debug_mp():
    """Depurar o payload enviado ao Mercado Pago."""
    print("\nDepuração do payload do Mercado Pago")
    print("===================================")
    
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
        
        # Mostrar o payload exato que será enviado
        print("\nPayload a ser enviado ao Mercado Pago:")
        print(json.dumps(preference_data, indent=2))
        
        # Investigar se o SDK está modificando o payload
        print("\nInvestigando SDK do Mercado Pago:")
        sdk_version = getattr(mercadopago, "__version__", "Desconhecida")
        print(f"Versão do SDK: {sdk_version}")
        print(f"Tipo do SDK: {type(sdk)}")
        
        # Tentar acessar e modificar o objeto para correção
        print("\nTentando corrigir manualmente o payload:")
        if hasattr(sdk.preference(), "create"):
            original_create = sdk.preference().create
            
            # Criar uma função wrapper para analisar o payload
            def debug_create(data):
                print(f"Dados recebidos pelo wrapper: {json.dumps(data, indent=2)}")
                # Correção manual para o caso do campo estar sendo alterado
                if "notification_url" in data and "notificaction_url" not in data:
                    print("Adicionando campo correto 'notification_url'")
                # Chamar função original
                return original_create(data)
            
            # Substituir temporariamente o método create
            sdk.preference().create = debug_create
            
            # Chamar a API com nosso wrapper
            print("\nEnviando requisição...")
            response = sdk.preference().create(preference_data)
            print(f"\nResposta recebida: {response}")
            return True
        else:
            print("Não foi possível acessar o método 'create' do SDK")
            return False
    
    except Exception as e:
        print(f"\nERRO: Exceção durante a depuração: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nDepuração da integração com o Mercado Pago")
    print("========================================")
    test_debug_mp()
    print("\nFim da depuração.")
