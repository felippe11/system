"""
Script para diagnosticar problemas com o reCAPTCHA v3.
Execute com: python debug_recaptcha_v3.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

def verificar_chaves_recaptcha():
    """Verifica as chaves do reCAPTCHA configuradas no ambiente."""
    
    print("=== DIAGNÓSTICO DE CONFIGURAÇÃO DO RECAPTCHA V3 ===\n")
    
    # Verifica a chave pública
    public_key = os.getenv("RECAPTCHA_PUBLIC_KEY", "")
    if not public_key:
        print("❌ ERRO: Chave pública (RECAPTCHA_PUBLIC_KEY) não está configurada!")
    else:
        print(f"✅ Chave pública encontrada: {public_key[:6]}...{public_key[-4:]} ({len(public_key)} caracteres)")
        
        # Verifica se parece ser uma chave v3 (geralmente começa com 6L)
        if public_key.startswith(("6L", "6l")):
            if "v3" in public_key.lower():
                print("   Parece ser uma chave válida para reCAPTCHA v3")
            else:
                print("   ⚠️ A chave não contém 'v3'. Verifique se é realmente uma chave para reCAPTCHA v3.")
        else:
            print("   ⚠️ O formato da chave pública é incomum. Verifique se é uma chave válida.")
    
    # Verifica a chave privada
    private_key = os.getenv("RECAPTCHA_PRIVATE_KEY", "")
    if not private_key:
        print("❌ ERRO: Chave privada (RECAPTCHA_PRIVATE_KEY) não está configurada!")
    else:
        print(f"✅ Chave privada encontrada: {private_key[:6]}...{private_key[-4:]} ({len(private_key)} caracteres)")
        
    print("\n=== VERIFICAÇÃO DE CONECTIVIDADE ===\n")
    
    # Testa a conectividade com o serviço do Google reCAPTCHA
    try:
        response = requests.get("https://www.google.com/recaptcha/api.js", timeout=5)
        if response.status_code == 200:
            print("✅ Conectividade com o servidor do reCAPTCHA está OK")
        else:
            print(f"❌ Erro ao acessar o servidor do reCAPTCHA: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Erro de conectividade: {str(e)}")
        
    print("\n=== RECOMENDAÇÕES ===\n")
    
    if not public_key or not private_key:
        print("1. Obtenha novas chaves reCAPTCHA v3 em: https://www.google.com/recaptcha/admin")
        print("2. Adicione as chaves no arquivo .env:")
        print("   RECAPTCHA_PUBLIC_KEY=sua_chave_publica_v3")
        print("   RECAPTCHA_PRIVATE_KEY=sua_chave_privada_v3")
    else:
        print("1. Verifique se os domínios autorizados no console do reCAPTCHA incluem:")
        print("   - localhost (para desenvolvimento local)")
        print("   - 127.0.0.1 (para desenvolvimento local)")
        print("   - O domínio de produção do seu site")
        print("\n2. Certifique-se de que as chaves são para reCAPTCHA v3.")
        print("   Se estiver usando chaves v2, crie um novo site no console com o tipo 'v3'")
        
    print("\n3. Para testar o reCAPTCHA v3 na sua aplicação:")
    print("   - Abra o console do navegador (F12) para ver erros")
    print("   - Verifique os logs do servidor para detalhes sobre falhas")

if __name__ == "__main__":
    verificar_chaves_recaptcha()
