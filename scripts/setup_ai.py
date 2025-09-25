#!/usr/bin/env python3
"""
Script de configuração da API de IA
Configura automaticamente os serviços de IA disponíveis
"""

import os
import sys
import requests
import json
from pathlib import Path

def check_huggingface_connection(api_key, model_id):
    """Verifica conexão com Hugging Face"""
    try:
        url = f"https://api-inference.huggingface.co/models/{model_id}"
        headers = {'Authorization': f'Bearer {api_key}'}
        
        response = requests.post(url, headers=headers, json={
            'inputs': 'test',
            'parameters': {'max_new_tokens': 10}
        }, timeout=10)
        
        return response.status_code == 200
    except:
        return False

def check_tgi_connection(endpoint):
    """Verifica conexão com TGI"""
    try:
        url = f"{endpoint}/v1/chat/completions"
        response = requests.post(url, json={
            'model': 'tgi',
            'messages': [{'role': 'user', 'content': 'test'}],
            'max_tokens': 10
        }, timeout=10)
        
        return response.status_code == 200
    except:
        return False

def create_env_file():
    """Cria arquivo .env com configurações de IA"""
    env_content = """# Configurações de IA - Gerado automaticamente

# Hugging Face
HUGGINGFACE_API_KEY=
HUGGINGFACE_MODEL_ID=microsoft/DialoGPT-medium
HUGGINGFACE_API_URL=https://api-inference.huggingface.co/models

# Text Generation Inference (TGI)
USE_TGI=false
TGI_ENDPOINT=http://localhost:3000

# Configurações Avançadas
REQUEST_TIMEOUT=30
MAX_RETRIES=3
ENABLE_FALLBACK=true
"""
    
    env_path = Path('.env')
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write(env_content)
        print("✅ Arquivo .env criado com configurações padrão")
    else:
        print("⚠️  Arquivo .env já existe")

def test_services():
    """Testa todos os serviços configurados"""
    print("\n🔍 Testando serviços de IA...")
    
    # Verificar Hugging Face
    hf_key = os.getenv('HUGGINGFACE_API_KEY')
    hf_model = os.getenv('HUGGINGFACE_MODEL_ID', 'microsoft/DialoGPT-medium')
    
    if hf_key:
        print(f"🤗 Testando Hugging Face com modelo {hf_model}...")
        if check_huggingface_connection(hf_key, hf_model):
            print("✅ Hugging Face: Conectado")
        else:
            print("❌ Hugging Face: Falha na conexão")
    else:
        print("⚠️  Hugging Face: API Key não configurada")
    
    # Verificar TGI
    use_tgi = os.getenv('USE_TGI', 'false').lower() == 'true'
    tgi_endpoint = os.getenv('TGI_ENDPOINT', 'http://localhost:3000')
    
    if use_tgi:
        print(f"🚀 Testando TGI em {tgi_endpoint}...")
        if check_tgi_connection(tgi_endpoint):
            print("✅ TGI: Conectado")
        else:
            print("❌ TGI: Falha na conexão")
    else:
        print("⚠️  TGI: Desabilitado")
    
    print("✅ Fallback: Sempre disponível")

def install_tgi():
    """Instala e configura TGI"""
    print("\n🚀 Configurando Text Generation Inference...")
    
    try:
        import subprocess
        
        # Instalar TGI
        print("📦 Instalando TGI...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'text-generation-inference'], check=True)
        
        print("✅ TGI instalado com sucesso")
        print("\n📋 Para executar o TGI, use:")
        print(f"text-generation-inference --model-id {os.getenv('HUGGINGFACE_MODEL_ID', 'microsoft/DialoGPT-medium')} --port 3000")
        
    except subprocess.CalledProcessError:
        print("❌ Erro ao instalar TGI")
    except Exception as e:
        print(f"❌ Erro: {e}")

def show_recommendations():
    """Mostra recomendações de configuração"""
    print("\n💡 Recomendações:")
    print("1. Para melhor qualidade em português, use: neuralmind/bert-base-portuguese-cased")
    print("2. Para desenvolvimento local, configure TGI com USE_TGI=true")
    print("3. Para produção, use Hugging Face com API key válida")
    print("4. Sempre mantenha fallback habilitado para garantir funcionamento")

def main():
    """Função principal"""
    print("🤖 Configurador da API de IA")
    print("=" * 40)
    
    # Carregar variáveis de ambiente
    from dotenv import load_dotenv
    load_dotenv()
    
    # Criar arquivo .env se não existir
    create_env_file()
    
    # Testar serviços
    test_services()
    
    # Mostrar opções
    print("\n📋 Opções disponíveis:")
    print("1. Instalar TGI")
    print("2. Testar serviços novamente")
    print("3. Mostrar recomendações")
    print("4. Sair")
    
    while True:
        try:
            choice = input("\nEscolha uma opção (1-4): ").strip()
            
            if choice == '1':
                install_tgi()
            elif choice == '2':
                test_services()
            elif choice == '3':
                show_recommendations()
            elif choice == '4':
                print("👋 Até logo!")
                break
            else:
                print("❌ Opção inválida")
                
        except KeyboardInterrupt:
            print("\n👋 Até logo!")
            break
        except Exception as e:
            print(f"❌ Erro: {e}")

if __name__ == '__main__':
    main()
