import os
import psycopg2
from sqlalchemy.pool import QueuePool

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if os.getenv("FLASK_ENV") == "production":
            raise RuntimeError("SECRET_KEY environment variable not set")
        SECRET_KEY = "6LcKl2YrAAAAAJ60mTLQ16l37kOmVXl8MDRy0bcy"  # Fixed key for development

    # URLs dos bancos de dados
    DB_ONLINE = os.getenv('DB_ONLINE')
    DB_LOCAL = os.getenv('DB_LOCAL') or f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"

    # Testa a conexão com o banco online
    def test_db_connection(db_uri):
        if not db_uri:
            return False
        try:
            conn = psycopg2.connect(db_uri, connect_timeout=10)
            conn.close()
            return True
        except Exception:
            return False

    @staticmethod
    def build_engine_options(uri):
        if uri.startswith('sqlite'):
            return {}

        return {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
            'pool_recycle': 1800,
            'pool_pre_ping': True,
            'connect_args': {'connect_timeout': 10},
        }

    # Define qual banco de dados será usado
    SQLALCHEMY_DATABASE_URI = DB_ONLINE if test_db_connection(DB_ONLINE) else DB_LOCAL

    # Configurações de pool de conexões
    SQLALCHEMY_ENGINE_OPTIONS = build_engine_options(SQLALCHEMY_DATABASE_URI)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuração para envio de e-mails via Gmail
    MAIL_SERVER = 'smtp.gmail.com'  # Servidor SMTP do Gmail
    MAIL_PORT = 587  # Porta para envio de e-mails
    MAIL_USE_TLS = True  # Usa TLS para segurança
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')  # Seu e-mail
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')  # Sua senha
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_USERNAME')  # O e-mail que enviará as mensagens

    # Chaves do reCAPTCHA
    RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY') or ''
    RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY') or ''
