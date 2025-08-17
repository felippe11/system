
"""Script para diagnosticar problemas com o reCAPTCHA v3."""
import logging
import os
import sys

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

def verificar_chaves_recaptcha():
    """Verifica as chaves do reCAPTCHA configuradas no ambiente."""
    
    logger.info("=== DIAGNÓSTICO DE CONFIGURAÇÃO DO RECAPTCHA V3 ===\n")
    
    # Verifica a chave pública
    public_key = os.getenv("RECAPTCHA_PUBLIC_KEY", "")
    if not public_key:
        logger.error(
            "❌ ERRO: Chave pública (RECAPTCHA_PUBLIC_KEY) não está configurada!"
        )
    else:
        logger.info(
            "✅ Chave pública encontrada: %s...%s (%s caracteres)",
            public_key[:6],
            public_key[-4:],
            len(public_key),
        )
        
        # Verifica se parece ser uma chave v3 (geralmente começa com 6L)
        if public_key.startswith(("6L", "6l")):
            if "v3" in public_key.lower():
                logger.info("   Parece ser uma chave válida para reCAPTCHA v3")
            else:
                logger.warning(
                    "   ⚠️ A chave não contém 'v3'. Verifique se é realmente uma chave para reCAPTCHA v3."
                )
        else:
            logger.warning(
                "   ⚠️ O formato da chave pública é incomum. Verifique se é uma chave válida."
            )
    
    # Verifica a chave privada
    private_key = os.getenv("RECAPTCHA_PRIVATE_KEY", "")
    if not private_key:
        logger.error(
            "❌ ERRO: Chave privada (RECAPTCHA_PRIVATE_KEY) não está configurada!"
        )
    else:
        logger.info(
            "✅ Chave privada encontrada: %s...%s (%s caracteres)",
            private_key[:6],
            private_key[-4:],
            len(private_key),
        )
        
    logger.info("\n=== VERIFICAÇÃO DE CONECTIVIDADE ===\n")
    
    # Testa a conectividade com o serviço do Google reCAPTCHA
    try:
        response = requests.get("https://www.google.com/recaptcha/api.js", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Conectividade com o servidor do reCAPTCHA está OK")
        else:
            logger.error(
                "❌ Erro ao acessar o servidor do reCAPTCHA: HTTP %s",
                response.status_code,
            )
    except Exception as e:
        logger.error("❌ Erro de conectividade: %s", str(e))
        
    logger.info("\n=== RECOMENDAÇÕES ===\n")
    
    if not public_key or not private_key:
        logger.info(
            "1. Obtenha novas chaves reCAPTCHA v3 em: https://www.google.com/recaptcha/admin"
        )
        logger.info("2. Adicione as chaves no arquivo .env:")
        logger.info("   RECAPTCHA_PUBLIC_KEY=sua_chave_publica_v3")
        logger.info("   RECAPTCHA_PRIVATE_KEY=sua_chave_privada_v3")
    else:
        logger.info("1. Verifique se os domínios autorizados no console do reCAPTCHA incluem:")
        logger.info("   - localhost (para desenvolvimento local)")
        logger.info("   - 127.0.0.1 (para desenvolvimento local)")
        logger.info("   - O domínio de produção do seu site")
        logger.info("\n2. Certifique-se de que as chaves são para reCAPTCHA v3.")
        logger.info(
            "   Se estiver usando chaves v2, crie um novo site no console com o tipo 'v3'"
        )
        
    logger.info("\n3. Para testar o reCAPTCHA v3 na sua aplicação:")
    logger.info("   - Abra o console do navegador (F12) para ver erros")
    logger.info("   - Verifique os logs do servidor para detalhes sobre falhas")

if __name__ == "__main__":
    verificar_chaves_recaptcha()

