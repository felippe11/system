import os
import logging
import json
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tentar importar o módulo mercadopago
try:
    import mercadopago
    logger.info("Módulo mercadopago importado com sucesso")
except ImportError as e:
    logger.error("Erro ao importar mercadopago: %s", e)
    logger.error("\nO módulo mercadopago não está instalado.")
    logger.error("Por favor, instale-o usando: pip install mercadopago")
    sys.exit(1)

def test_debug_mp():
    """Depurar o payload enviado ao Mercado Pago."""
    logger.info("\nDepuração do payload do Mercado Pago")
    logger.info("===================================")
    
    # Verificar se o token está configurado
    token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not token:
        logger.error("ERRO: MERCADOPAGO_ACCESS_TOKEN não está definido no ambiente.")
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
        logger.info("\nPayload a ser enviado ao Mercado Pago:")
        logger.info(json.dumps(preference_data, indent=2))
        
        # Investigar se o SDK está modificando o payload
        logger.info("\nInvestigando SDK do Mercado Pago:")
        sdk_version = getattr(mercadopago, "__version__", "Desconhecida")
        logger.info("Versão do SDK: %s", sdk_version)
        logger.info("Tipo do SDK: %s", type(sdk))
        
        # Tentar acessar e modificar o objeto para correção
        logger.info("\nTentando corrigir manualmente o payload:")
        if hasattr(sdk.preference(), "create"):
            original_create = sdk.preference().create
            
            # Criar uma função wrapper para analisar o payload
            def debug_create(data):
                logger.info("Dados recebidos pelo wrapper: %s", json.dumps(data, indent=2))
                # Correção manual para o caso do campo estar sendo alterado
                if "notification_url" in data and "notificaction_url" not in data:
                    logger.info("Adicionando campo correto 'notification_url'")
                # Chamar função original
                return original_create(data)
            
            # Substituir temporariamente o método create
            sdk.preference().create = debug_create
            
            # Chamar a API com nosso wrapper
            logger.info("\nEnviando requisição...")
            response = sdk.preference().create(preference_data)
            logger.info("\nResposta recebida: %s", response)
            return True
        else:
            logger.error("Não foi possível acessar o método 'create' do SDK")
            return False
    
    except Exception as e:
        logger.error("\nERRO: Exceção durante a depuração: %s", str(e))
        return False

if __name__ == "__main__":
    logger.info("\nDepuração da integração com o Mercado Pago")
    logger.info("========================================")
    test_debug_mp()
    logger.info("\nFim da depuração.")
