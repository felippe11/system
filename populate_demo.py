"""Script de demonstração para popular o banco de dados PostgreSQL."""
import logging
import os
import traceback

logger = logging.getLogger(__name__)

try:
    from app import create_app, db
    from populate_script import popular_banco

    # Configuração do banco de dados PostgreSQL
    os.environ["DATABASE_URL"] = "postgresql://iafap:123456@localhost:5432/iafap_database"

    # Cria e configura a aplicação Flask
    app = create_app()

    # Executa dentro do contexto da aplicação
    with app.app_context():
        logger.info(
            "Iniciando população do banco com credenciais PostgreSQL..."
        )
        logger.info(
            "URL do banco: postgresql://iafap:123456@localhost:5432/iafap_database"
        )
        dados = popular_banco()
        logger.info("População concluída com sucesso!")

        # Exibe alguns números
        logger.info("\nResumo dos dados criados:")
        logger.info("- %s clientes", len(dados["clientes"]))
        logger.info("- %s eventos", len(dados["eventos"]))
        logger.info("- %s ministrantes", len(dados["ministrantes"]))
        logger.info("- %s oficinas", len(dados["oficinas"]))
        logger.info("- %s usuários", len(dados["usuarios"]))
        logger.info("- %s inscrições", len(dados["inscricoes"]))
        logger.info("- %s submissões", len(dados["submissoes"]))
        logger.info("- %s reviews", len(dados["reviews"]))
        logger.info("- %s assignments", len(dados["assignments"]))
        logger.info("- %s arquivos binários", len(dados["arquivos"]))
        logger.info(
            "- %s agendamentos de visita",
            len(dados["agendamentos"]),
        )
except Exception as e:
    logger.error("Erro durante a execução: %s", e)
    traceback.print_exc()
    logger.info(
        "\nDica: Verifique se o banco de dados PostgreSQL está em execução e acessível "
        "com as credenciais fornecidas."
    )
    logger.info("\nResumo dos dados criados:")
    logger.info("- %s clientes", len(dados["clientes"]))
    logger.info("- %s eventos", len(dados["eventos"]))
    logger.info("- %s usuários", len(dados["usuarios"]))
    logger.info("- %s inscrições", len(dados["inscricoes"]))
