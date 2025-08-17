import logging

from app import app
from extensions import db
from sqlalchemy import text

logger = logging.getLogger(__name__)

with app.app_context():
    try:
        # Adicionar a coluna taxa_diferenciada à tabela configuracao_cliente
        db.session.execute(
            text(
                "ALTER TABLE configuracao_cliente ADD COLUMN IF NOT EXISTS"
                " taxa_diferenciada NUMERIC(5,2);"
            )
        )
        db.session.commit()
        logger.info(
            "Coluna taxa_diferenciada adicionada com sucesso à tabela configuracao_cliente!"
        )
    except Exception as e:
        logger.error("Erro ao adicionar coluna: %s", e)
