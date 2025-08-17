"""
Patch para corrigir a URL de notificação em requisições do Mercado Pago.

Este arquivo deve ser importado no app.py antes de iniciar o aplicativo.
"""

import logging
from flask import request, current_app, url_for
import os

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Função para gerar URLs absolutas corretamente
def patched_external_url(endpoint, **values):
    """
    Versão corrigida da função external_url para garantir URLs absolutas válidas.
    """
    # Usar APP_BASE_URL se estiver definido
    base_url = os.getenv("APP_BASE_URL")
    if base_url:
        # Garantir que a base URL seja válida
        if not base_url.startswith(('http://', 'https://')):
            base_url = 'https://' + base_url
        
        # Remover qualquer barra final
        base_url = base_url.rstrip("/")
        
        # Gerar URL relativo e combinar com a base
        path = url_for(endpoint, _external=False, **values)
        return base_url + path
    
    # Usar SERVER_NAME se disponível
    server_name = current_app.config.get('SERVER_NAME')
    if server_name:
        # Protocolo preferido
        scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'https')
        path = url_for(endpoint, _external=False, **values)
        return f"{scheme}://{server_name}{path}"
    
    # Usar o host da requisição atual
    if request and request.host:
        scheme = request.scheme or 'https'
        path = url_for(endpoint, _external=False, **values)
        return f"{scheme}://{request.host}{path}"
    
    # Ultimo fallback - gerar URL absoluta
    return url_for(endpoint, _external=True, **values)

# Função para corrigir as URLs de notificação do Mercado Pago
def fix_mp_notification_url(url):
    """
    Garante que a URL de notificação esteja em um formato aceitável pelo Mercado Pago.
    """
    # Verificar se a URL é absoluta
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Verificar se a URL não é localhost ou 127.0.0.1 (não aceito pelo MP)
    if 'localhost' in url or '127.0.0.1' in url:
        # Usar uma URL substituta válida para o Mercado Pago
        return os.getenv("APP_BASE_URL", "https://sistema.evento.com") + "/mercadopago/webhook"
    
    return url

# Função para criar a preferência de pagamento do Mercado Pago
def create_mp_preference(sdk, preference_data):
    """
    Cria uma preferência de pagamento no Mercado Pago de forma segura.
    """
    # Verificar se há notification_url nos dados
    if "notification_url" in preference_data:
        # Corrigir a URL
        notification_url = fix_mp_notification_url(preference_data["notification_url"])
        preference_data["notification_url"] = notification_url
        logger.info(f"URL de notificação corrigida: {notification_url}")
        
        # O Mercado Pago está rejeitando com o nome correto 'notification_url'
        # Tentando com o nome alternativo 'notificaction_url' (com 'c' extra)
        preference_data["notificaction_url"] = notification_url
    
    # Verificar URLs de retorno para garantir que sejam válidas
    if "back_urls" in preference_data:
        for key, url in preference_data["back_urls"].items():
            if not url.startswith(('http://', 'https://')):
                preference_data["back_urls"][key] = 'https://' + url
    
    # Criar a preferência
    logger.info(f"Criando preferência MP com dados: {preference_data}")
    return sdk.preference().create(preference_data)

# Documentação de uso
usage_doc = """
Para usar este patch:

1. Importe no app.py:
   from mp_fix_patch import patched_external_url, create_mp_preference

2. Substitua a função external_url:
   utils.external_url = patched_external_url

3. Use create_mp_preference no lugar de sdk.preference().create:
   pref = create_mp_preference(sdk, preference_data)
"""

if __name__ == "__main__":
    import logging

    logger = logging.getLogger(__name__)
    logger.info(usage_doc)
