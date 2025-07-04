"""
Script de demonstração para popular o banco de dados PostgreSQL
"""
import os
import traceback

try:
    from app import create_app, db
    from populate_script import popular_banco

    # Configuração do banco de dados PostgreSQL
    os.environ["DATABASE_URL"] = "postgresql://iafap:123456@localhost:5432/iafap_database"

    # Cria e configura a aplicação Flask
    app = create_app()

    # Executa dentro do contexto da aplicação
    with app.app_context():
        print("Iniciando população do banco com credenciais PostgreSQL...")
        print("URL do banco: postgresql://iafap:123456@localhost:5432/iafap_database")
        dados = popular_banco()
        print("População concluída com sucesso!")
        
        # Exibe alguns números
        print("\nResumo dos dados criados:")
        print(f"- {len(dados['clientes'])} clientes")
        print(f"- {len(dados['eventos'])} eventos")
        print(f"- {len(dados['ministrantes'])} ministrantes")
        print(f"- {len(dados['oficinas'])} oficinas")
        print(f"- {len(dados['usuarios'])} usuários")
        print(f"- {len(dados['inscricoes'])} inscrições")
        print(f"- {len(dados['submissoes'])} submissões")
        print(f"- {len(dados['reviews'])} reviews")
        print(f"- {len(dados['assignments'])} assignments")
        print(f"- {len(dados['arquivos'])} arquivos binários")
        print(f"- {len(dados['agendamentos'])} agendamentos de visita")
except Exception as e:
    print(f"Erro durante a execução: {e}")
    traceback.print_exc()
    print("\nDica: Verifique se o banco de dados PostgreSQL está em execução e acessível com as credenciais fornecidas.")
    print("\nResumo dos dados criados:")
    print(f"- {len(dados['clientes'])} clientes")
    print(f"- {len(dados['eventos'])} eventos")
    print(f"- {len(dados['usuarios'])} usuários")
    print(f"- {len(dados['inscricoes'])} inscrições")
