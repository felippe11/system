#!/usr/bin/env python3

import requests
import sys

def test_iniciar_revisao_route():
    """Testa se a rota /revisor/iniciar_revisao/794 está funcionando."""
    
    url = "http://localhost:5000/revisor/iniciar_revisao/794"
    
    try:
        print(f"Testando rota: {url}")
        response = requests.get(url, allow_redirects=False)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            print(f"Redirecionamento para: {response.headers.get('Location')}")
        elif response.status_code == 200:
            print("Página carregada com sucesso!")
            print(f"Conteúdo (primeiros 500 chars): {response.text[:500]}")
        else:
            print(f"Erro inesperado: {response.status_code}")
            print(f"Conteúdo: {response.text[:500]}")
            
    except requests.exceptions.ConnectionError:
        print("Erro: Não foi possível conectar ao servidor. Verifique se o Flask está rodando.")
    except Exception as e:
        print(f"Erro inesperado: {e}")

if __name__ == "__main__":
    test_iniciar_revisao_route()