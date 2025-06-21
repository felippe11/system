"""
Repara a integração com o Mercado Pago adicionando o patch 
diretamente ao arquivo routes/inscricao_routes.py
"""

import os
import sys
import re

def apply_mp_fix():
    """
    Aplica a correção ao arquivo inscricao_routes.py
    """
    filepath = os.path.join('routes', 'inscricao_routes.py')
    
    if not os.path.exists(filepath):
        print(f"Erro: O arquivo {filepath} não foi encontrado.")
        return False
        
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Importar o módulo de correção no início do arquivo
    import_pattern = r"import os\s+"
    import_replacement = "import os\nfrom mp_fix_patch import fix_mp_notification_url, create_mp_preference\n"
    
    if "from mp_fix_patch import" not in content:
        content = re.sub(import_pattern, import_replacement, content)
    
    # Substituir a criação de preferência direta por nossa função segura
    old_code = r"(\s+)pref = sdk\.preference\(\)\.create\(preference_data\)"
    new_code = r"\1# Usar a função segura de criação de preferência\n\1pref = create_mp_preference(sdk, preference_data)"
    
    if "create_mp_preference(sdk, preference_data)" not in content:
        content = re.sub(old_code, new_code, content)
    
    # Substituir a construção da URL de notificação para usar nossa função segura
    old_url_code = r"(\s+)notification_url = external_url\(\"mercadopago_routes\.webhook_mp\"\)"
    new_url_code = r"\1# Usar URL segura para notificação\n\1notification_url = fix_mp_notification_url(external_url(\"mercadopago_routes.webhook_mp\"))"
    
    if "fix_mp_notification_url" not in content:
        content = re.sub(old_url_code, new_url_code, content)
    
    # Salvar as alterações
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"Arquivo {filepath} atualizado com sucesso!")
    return True

def main():
    """
    Função principal que aplica os patches necessários
    """
    print("\nAplicando correções para integração com Mercado Pago...")
    
    # Verificar se estamos no diretório raiz do projeto
    if not os.path.exists('app.py'):
        print("Erro: Este script deve ser executado no diretório raiz do projeto.")
        return False
    
    # Aplicar correção ao inscricao_routes.py
    if apply_mp_fix():
        print("\nCorreção aplicada com sucesso!")
        print("\nPróximos passos:")
        print("1. Reinicie a aplicação: python app.py")
        print("2. Teste o fluxo de cadastro de participante")
        print("3. Verifique os logs para confirmar que as URLs estão corretas")
        return True
    else:
        print("\nErro ao aplicar correções.")
        return False

if __name__ == "__main__":
    main()
