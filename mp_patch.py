"""
Script para corrigir problema de notificação no Mercado Pago.
Este script cria um monkey patch para o SDK do Mercado Pago para garantir
que a URL de notificação seja enviada com o nome correto.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Logger do módulo
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

try:
    import mercadopago
    logger.info("Módulo mercadopago importado com sucesso")
except ImportError:
    logger.error("Módulo mercadopago não encontrado. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mercadopago"])
    import mercadopago
    logger.info("Módulo mercadopago instalado e importado com sucesso")

# Obter a versão original do módulo
original_preference_create = None
if hasattr(mercadopago.sdk.SDK, "preference"):
    sdk_instance = mercadopago.SDK("dummy_token")  # Apenas para obter a estrutura
    preference_instance = sdk_instance.preference()
    if hasattr(preference_instance, "create"):
        original_preference_create = preference_instance.create
        logger.info("Método original de criação de preferência localizado")

def patched_preference_create(self, preference_data):
    """
    Wrapper para o método create() da classe Preference do SDK do Mercado Pago.
    Corrige o problema do nome do campo notification_url que estava sendo enviado como
    notificaction_url (com 'c' adicional).
    """
    if "notification_url" in preference_data and not preference_data.get("notificaction_url"):
        logger.info(f"Aplicando patch para URL de notificação: {preference_data['notification_url']}")
        # Se aparecer o erro, é possível que o SDK esteja renomeando o campo
        # Nesse caso, vamos garantir que ambos os campos existam
        preference_data["notificaction_url"] = preference_data["notification_url"]
    
    if original_preference_create:
        return original_preference_create(self, preference_data)
    else:
        logger.error("Método original não encontrado, não foi possível aplicar o patch")
        return None

def apply_patch():
    """Aplica o monkey patch no SDK do Mercado Pago."""
    if original_preference_create:
        # Substituir o método original pelo nosso método corrigido
        mercadopago.resources.preference.Preference.create = patched_preference_create
        logger.info("Monkey patch aplicado com sucesso no SDK do Mercado Pago")
        return True
    else:
        logger.error("Não foi possível aplicar o patch: método original não encontrado")
        return False

def test_patch():
    """Testa o patch aplicado."""
    token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not token:
        logger.error("MERCADOPAGO_ACCESS_TOKEN não configurado")
        return False
    
    sdk = mercadopago.SDK(token)
    
    # Dados de teste
    test_data = {
        "items": [{"id": "test", "title": "Teste", "quantity": 1, "currency_id": "BRL", "unit_price": 10}],
        "notification_url": "https://sistema.evento.com/webhook",
        "external_reference": "test-ref"
    }
    
    try:
        response = sdk.preference().create(test_data)
        if response.get("status") == 201:
            logger.info("Preferência criada com sucesso após aplicar o patch!")
            logger.info(f"ID da preferência: {response.get('response', {}).get('id')}")
            return True
        else:
            logger.error(f"Falha ao criar preferência após patch: {response}")
            return False
    except Exception as e:
        logger.exception(f"Exceção ao testar patch: {e}")
        return False

if __name__ == "__main__":
    logger.info("Iniciando aplicação do patch para o SDK do Mercado Pago")
    
    if apply_patch():
        logger.info("Patch aplicado com sucesso!")
        if test_patch():
            logger.info("Teste do patch concluído com sucesso!")
        else:
            logger.error("Teste do patch falhou!")
    else:
        logger.error("Falha ao aplicar o patch!")
        
    logger.info("Fim do processo.")
