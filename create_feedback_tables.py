
from app import create_app
from extensions import db
from models.open_feedback_models import (
    FeedbackAbertoPergunta,
    FeedbackAbertoDia,
    FeedbackAbertoDiaPergunta,
    FeedbackAbertoEnvio,
    FeedbackAbertoResposta
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_feedback_tables():
    app = create_app()
    with app.app_context():
        logger.info("Starting to create feedback tables...")
        try:
            # Create tables directly
            # SQLAlchemy will only create tables that don't exist
            db.create_all()
            logger.info("Tables creation process completed.")
            
            # Verify if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            feedback_tables = [
                "feedback_aberto_perguntas",
                "feedback_aberto_dias",
                "feedback_aberto_dia_perguntas",
                "feedback_aberto_envios",
                "feedback_aberto_respostas"
            ]
            
            for table in feedback_tables:
                if table in tables:
                    logger.info(f"Table '{table}' exists.")
                else:
                    logger.error(f"Table '{table}' does NOT exist.")
                    
        except Exception as e:
            logger.error(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_feedback_tables()
