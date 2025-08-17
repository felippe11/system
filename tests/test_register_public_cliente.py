import pytest
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models.user import Cliente

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['RECAPTCHA_PUBLIC_KEY'] = 'test'
    app.config['RECAPTCHA_PRIVATE_KEY'] = 'test'
    with app.app_context():
        db.create_all()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def test_registrar_cliente_sucesso(client, app):
    data = {
        'nome': 'Novo',
        'email': 'novo@example.com',
        'senha': '123',
        'g-recaptcha-response': 'dummy'
    }
    resp = client.post('/registrar_cliente', data=data, follow_redirects=True)
    assert resp.status_code in (200, 302)
    assert b'Login AppFiber' in resp.data


def test_registrar_cliente_falha_captcha(client, app):
    app.config['TESTING'] = False
    data = {
        'nome': 'Fail',
        'email': 'fail@example.com',
        'senha': '123'
    }
    resp = client.post('/registrar_cliente', data=data)
    assert resp.status_code == 200
    assert b'captcha' in resp.data.lower()
