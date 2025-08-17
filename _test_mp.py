import logging
import sys
import os
from services.mp_service import get_sdk

# Logger do módulo
logger = logging.getLogger(__name__)

def main():
    logger.info("Testando conexão com o Mercado Pago")
    
    # Obtém o SDK
    sdk = get_sdk()
    if sdk is None:
        logger.error("Falha ao inicializar o SDK do Mercado Pago")
        return 1
        
    logger.info("SDK do Mercado Pago inicializado com sucesso")
    
    # Dados básicos de uma preferência
    preference_data = {
        "items": [
            {
                "id": "test_item",
                "title": "Teste de inscrição",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": 10.0
            }
        ],
        "payer": {"email": "test@example.com", "name": "Test User"},
        "external_reference": "test_123",
    }
    
    try:
        # Tenta criar uma preferência
        pref = sdk.preference().create(preference_data)
        logger.info(f"Preferência de teste criada com sucesso: {pref.get('status', 'N/A')}")
        logger.info(f"ID da preferência: {pref.get('response', {}).get('id', 'N/A')}")
        return 0
    except Exception as e:
        logger.error(f"Erro ao criar preferência: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Detalhes do erro: {e.response}")
        return 1
    
if __name__ == "__main__":
    sys.exit(main())
