import logging

from app import app
from extensions import db
from sqlalchemy import text

logger = logging.getLogger(__name__)

with app.app_context():
    # Obter conexão
    conn = db.engine.connect()
    
    # Consultar informações da tabela configuracao_cliente
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'configuracao_cliente'"))
    
    logger.info("Colunas na tabela configuracao_cliente:")
    for row in result:
        logger.info("- %s: %s", row[0], row[1])
    
    # Verificar se a coluna taxa_diferenciada existe
    result = conn.execute(text("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'configuracao_cliente' AND column_name = 'taxa_diferenciada'"))
    taxa_exists = result.scalar() > 0
    
    logger.info(
        "\nA coluna taxa_diferenciada %s na tabela.",
        "existe" if taxa_exists else "NÃO existe",
    )
    
    if not taxa_exists:
        logger.info("\nScript SQL para adicionar a coluna manualmente:")
        logger.info(
            "ALTER TABLE configuracao_cliente ADD COLUMN taxa_diferenciada NUMERIC(5, 2);"
        )
        
        # Adicionar a coluna manualmente
        try:
            conn.execute(
                text(
                    "ALTER TABLE configuracao_cliente ADD COLUMN taxa_diferenciada"
                    " NUMERIC(5, 2)"
                )
            )
            conn.commit()  # Importante para confirmar a transação
            logger.info("\nColuna taxa_diferenciada adicionada com sucesso!")
        except Exception as e:
            logger.error("\nErro ao adicionar coluna: %s", str(e))
    
    conn.close()
