import os
from sqlalchemy.pool import QueuePool

# ------------------------------------------------------------------ #
#  Helpers                                                           #
# ------------------------------------------------------------------ #
def normalize_pg(uri: str | bytes) -> str:
    """Garante o prefixo aceito pelo SQLAlchemy/psycopg2.

    Aceita `str` ou `bytes` e sempre retorna `str`. Quando `uri` é
    fornecido como bytes, ele é decodificado usando UTF-8 e, em caso de
    falha, Latin-1 é utilizado como "fallback".
    """
    if isinstance(uri, bytes):
        try:
            uri = uri.decode("utf-8")
        except UnicodeDecodeError:
            uri = uri.decode("latin-1")
    return uri.replace("postgresql://", "postgresql+psycopg2://", 1)


# ------------------------------------------------------------------ #
#  Config                                                            #
# ------------------------------------------------------------------ #
class Config:
    # ------------------------------------------------------------------ #
    #  Chave secreta                                                     #
    # ------------------------------------------------------------------ #
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret-key"

    # ------------------------------------------------------------------ #
    #  Parâmetros individuais (podem vir de .env ou variáveis do sistema) #
    # ------------------------------------------------------------------ #
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASS = os.getenv("DB_PASS", "postgres")          # <- senha padrão
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "iafap_database")

    # Se existir DATABASE_URL / DB_ONLINE, ele tem prioridade
    _URI_FROM_ENV = (
        os.getenv("DB_ONLINE") or
        os.getenv("DATABASE_URL")
    )

    SQLALCHEMY_DATABASE_URI = normalize_pg(
        _URI_FROM_ENV
        or f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

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
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = MAIL_USERNAME

    # ------------------------------------------------------------------ #
    #  reCAPTCHA                                                         #
    # ------------------------------------------------------------------ #
    RECAPTCHA_PUBLIC_KEY = os.getenv("RECAPTCHA_PUBLIC_KEY", "")
    RECAPTCHA_PRIVATE_KEY = os.getenv("RECAPTCHA_PRIVATE_KEY", "")
