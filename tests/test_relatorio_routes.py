import os
import sys
import types
from unittest.mock import patch

import pytest
from werkzeug.security import generate_password_hash

from config import Config
from app import create_app
from extensions import db
from models.user import Usuario

# Configure in-memory database
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)


@pytest.fixture
def app():
    os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
    os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
    sys.modules.pop('services.relatorio_service', None)
    sys.modules['transformers'] = types.SimpleNamespace(pipeline=lambda *a, **k: lambda *a2, **k2: None)
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        admin = Usuario(
            nome='Admin', cpf='1', email='admin@test',
            senha=generate_password_hash('123', method="pbkdf2:sha256"), formacao='x', tipo='admin'
        )
        db.session.add(admin)
        db.session.commit()
    yield app
    sys.modules.pop('transformers', None)


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post('/login', data={'email': 'admin@test', 'senha': '123'}, follow_redirects=True)


def test_relatorio_mensagem(client, app):
    login(client)
    with patch('routes.relatorio_routes.montar_relatorio_mensagem', return_value='MSG'):
        resp = client.get('/relatorio_mensagem')
    assert resp.status_code == 200
    assert b'MSG' in resp.data
    assert 'text/html' in resp.headers.get('Content-Type', '')
