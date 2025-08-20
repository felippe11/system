import os
from dotenv import load_dotenv

from sqlalchemy.pool import QueuePool

# Carrega o arquivo .env explicitamente
load_dotenv()

# ------------------------------------------------------------------ #
#  Helpers                                                           #
# ------------------------------------------------------------------ #
def normalize_pg(uri: str | bytes) -> str:
    """Garante o prefixo aceito pelo SQLAlchemy/psycopg2."""
    if isinstance(uri, bytes):
        uri = uri.decode()
    return uri.replace("postgresql://", "postgresql+psycopg2://", 1)


# ------------------------------------------------------------------ #
#  Config                                                            #
# ------------------------------------------------------------------ #
class Config:
    _URI_FROM_ENV = os.getenv("DATABASE_URL")
    # ------------------------------------------------------------------ #
    #  Chave secreta                                                     #
    # ------------------------------------------------------------------ #

    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is required; define a secure value."
        )
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")

if not DB_PASS:
    if DEBUG:
        DB_PASS = "postgres"  # fallback só para dev
    else:
        raise RuntimeError(
            "DB_PASS environment variable is required; set the database password."
        )

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "iafap_database")

    SQLALCHEMY_DATABASE_URI = normalize_pg(
        _URI_FROM_ENV
        or f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    @staticmethod
    def normalize_pg(uri: str | bytes) -> str:
        return normalize_pg(uri)

    @staticmethod
    def build_engine_options(uri: str) -> dict:
        """Return engine options for the given database URI."""
        options = dict(
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
        # Para conexões SQLite em testes, diversas opções de pool não se aplicam
        # e causam erros. Removemos "connect_args" e os parâmetros de pool
        # relacionados.
        if uri.startswith("sqlite:"):
            options.pop("connect_args", None)
            options.pop("pool_size", None)
            options.pop("max_overflow", None)
            options.pop("pool_timeout", None)
            options.pop("poolclass", None)
        return options

    # ------------------------------------------------------------------ #
    #  Pool de conexões                                                  #
    # ------------------------------------------------------------------ #
    SQLALCHEMY_ENGINE_OPTIONS = build_engine_options(SQLALCHEMY_DATABASE_URI)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ------------------------------------------------------------------ #
    #  E-mail                                                            #
    # ------------------------------------------------------------------ #
    # Configurações do provedor de e-mail (Mailjet)
    MAILJET_API_KEY = os.getenv("MAILJET_API_KEY") or os.getenv("MAIL_USERNAME", "")
    MAILJET_SECRET_KEY = (
        os.getenv("MAILJET_SECRET_KEY") or os.getenv("MAIL_PASSWORD", "")
    )

    MAIL_SERVER = "in-v3.mailjet.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = MAILJET_API_KEY
    MAIL_PASSWORD = MAILJET_SECRET_KEY
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # ------------------------------------------------------------------ #
    #  reCAPTCHA                                                         #
    # ------------------------------------------------------------------ #
    RECAPTCHA_PUBLIC_KEY = os.getenv("RECAPTCHA_PUBLIC_KEY", "")
    RECAPTCHA_PRIVATE_KEY = os.getenv("RECAPTCHA_PRIVATE_KEY", "")
    # Configurações extras que podem ser necessárias com versões mais recentes
    RECAPTCHA_VERIFY_SERVER = "https://www.google.com/recaptcha/api/siteverify"
    RECAPTCHA_PARAMETERS = {"hl": "pt-BR"}
    RECAPTCHA_DATA_ATTRS = {"theme": "light", "size": "normal"}
    # Para Flask-WTF 1.2+
    WTF_CSRF_TIME_LIMIT = 3600  # Tempo em segundos (1 hora)

    # ------------------------------------------------------------------ #
    #  Cache de arquivos estáticos                                       #
    # ------------------------------------------------------------------ #
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 ano

