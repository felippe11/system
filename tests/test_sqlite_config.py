from config import Config
from app import create_app


def test_create_app_sqlite_no_connect_args():
    Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
        Config.SQLALCHEMY_DATABASE_URI
    )
    app = create_app()
    assert 'connect_args' not in app.config['SQLALCHEMY_ENGINE_OPTIONS']
