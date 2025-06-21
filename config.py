import os
import psycopg2
from sqlalchemy.pool import QueuePool

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ------------------------------------------------------------------ #
#  Helpers                                                           #
# ------------------------------------------------------------------ #
def _normalize_pg_dsn(uri: str) -> str:
    """
    Se a string vier como 'postgresql+psycopg2://', converte para
    'postgresql://' para que psycopg2.connect aceite.
    """
    if uri and uri.startswith("postgresql+"):
        return uri.replace("postgresql+psycopg2://", "postgresql://", 1)
    return uri


# ------------------------------------------------------------------ #
#  Config                                                            #
# ------------------------------------------------------------------ #
class Config:
    # ------------------------------------------------------------------ #
    #  Chave secreta                                                     #
    # ------------------------------------------------------------------ #
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if os.getenv("FLASK_ENV") == "production":
            raise RuntimeError("SECRET_KEY environment variable not set")
        # Apenas para ambiente de desenvolvimento
        SECRET_KEY = "6LcKl2YrAAAAAJ60mTLQ16l37kOmVXl8MDRy0bcy"

    # ------------------------------------------------------------------ #
    #  Bancos de Dados                                                   #
    # ------------------------------------------------------------------ #
    DB_ONLINE = (
        os.getenv("DB_ONLINE")          # seu nome antigo
        or os.getenv("DATABASE_URL")    # padrão em muitos deploys
        or ""
    )
    DB_LOCAL = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"

    # -- testa rapidamente se o Postgres está acessível ---------------- #
    @staticmethod
    def test_db_connection(db_uri: str) -> bool:
        """
        Faz um `connect_timeout` rápido (5 s). Somente para Postgres.
        Outros dialetos retornam False para cair no SQLite local.
        """
        if not db_uri or db_uri.startswith("sqlite"):
            return False
        try:
            psycopg2.connect(_normalize_pg_dsn(db_uri), connect_timeout=5).close()
            return True
        except Exception:
            return False

    # URI final utilizada pelo SQLAlchemy
    SQLALCHEMY_DATABASE_URI = (
        DB_ONLINE if test_db_connection(DB_ONLINE) else DB_LOCAL
    )

    # ------------------------------------------------------------------ #
    #  Pool de conexões                                                  #
    # ------------------------------------------------------------------ #
    @staticmethod
    def build_engine_options(uri: str) -> dict:
        """Usa opções de pool só quando o banco não é SQLite."""
        if uri.startswith("sqlite"):
            return {}  # SQLite não suporta pool do mesmo jeito
        return dict(
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,   # 30 min
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )

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
