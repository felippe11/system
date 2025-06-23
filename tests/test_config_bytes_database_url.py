import os
import pytest

from config import Config, normalize_pg
from app import create_app


def test_create_app_with_bytes_database_url(monkeypatch):
    uri = b'sqlite:///:memory:'
    monkeypatch.setitem(os.environb, b'DATABASE_URL', uri)

    Config.SQLALCHEMY_DATABASE_URI = normalize_pg(uri)
    Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
        Config.SQLALCHEMY_DATABASE_URI
    )

    try:
        create_app()
    except UnicodeDecodeError:
        pytest.fail('create_app raised UnicodeDecodeError')
