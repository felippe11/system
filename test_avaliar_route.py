#!/usr/bin/env python3

import requests
import sys

def test_avaliar_route():
    """Testa se a rota /revisor/avaliar/794 está funcionando."""
    
    url = "http://localhost:5000/revisor/avaliar/794"
    
    try:
        print(f"Testando rota: {url}")
        response = requests.get(url, allow_redirects=True)
        
        print(f"Status Code: {response.status_code}")
        print(f"URL Final: {response.url}")
        
        if response.status_code == 200:
            print("Página carregada com sucesso!")
            # Verificar se contém "Acesso negado!"
            if "Acesso negado!" in response.text:
                print("❌ ERRO: Ainda contém 'Acesso negado!' na página")
            else:
                print("✅ SUCESSO: Página carregou sem erro de 'Acesso negado!'")
            
            # Verificar se é uma página de avaliação
            if "avaliacao" in response.text.lower() or "barema" in response.text.lower():
                print("✅ SUCESSO: Página de avaliação detectada")
            else:
                print("⚠️  AVISO: Não parece ser uma página de avaliação")
                
        else:
            print(f"Erro: {response.status_code}")
            print(f"Conteúdo (primeiros 500 chars): {response.text[:500]}")
            
    except requests.exceptions.ConnectionError:
        print("Erro: Não foi possível conectar ao servidor. Verifique se o Flask está rodando.")
    except Exception as e:
        print(f"Erro inesperado: {e}")

if __name__ == "__main__":
    test_avaliar_route()