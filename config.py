import os
import psycopg2
from sqlalchemy.pool import QueuePool

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if os.getenv("FLASK_ENV") == "production":
            raise RuntimeError("SECRET_KEY environment variable not set")
        SECRET_KEY = "dev_secret_key"  # Fixed key for development

    # URLs dos bancos de dados
    DB_ONLINE = 'postgresql://iafap:tOsydfgBrVx1o57X7oqznlABbwlFek84@dpg-cug5itl6l47c739tgung-a/iafap_database'
    DB_LOCAL = 'postgresql://iafap:iafap@localhost:5432/iafap_database'

    # Testa a conexão com o banco online
    def test_db_connection(db_uri):
        try:
            conn = psycopg2.connect(db_uri, connect_timeout=10)
            conn.close()
            return True
        except Exception:
            return False

    # Define qual banco de dados será usado
    SQLALCHEMY_DATABASE_URI = DB_ONLINE if test_db_connection(DB_ONLINE) else DB_LOCAL

    # Configurações de pool de conexões
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,  # Número máximo de conexões permanentes
        'max_overflow': 20,  # Número máximo de conexões temporárias
        'pool_timeout': 30,  # Tempo máximo de espera por uma conexão
        'pool_recycle': 1800,  # Recicla conexões após 30 minutos
        'pool_pre_ping': True,  # Verifica se a conexão está ativa antes de usar
        'connect_args': {
            'connect_timeout': 10  # Aumenta o timeout de conexão
        }
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuração para envio de e-mails via Gmail
    MAIL_SERVER = 'smtp.gmail.com'  # Servidor SMTP do Gmail
    MAIL_PORT = 587  # Porta para envio de e-mails
    MAIL_USE_TLS = True  # Usa TLS para segurança
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')  # Seu e-mail
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')  # Sua senha
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_USERNAME')  # O e-mail que enviará as mensagens
