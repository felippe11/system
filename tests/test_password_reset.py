from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
import os

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')

import utils
from models.user import Usuario
from werkzeug.security import generate_password_hash
import pytest

@pytest.fixture
def app():
    os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
    os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        user = Usuario(nome='User', cpf='123', email='user@test', senha=generate_password_hash('123', method="pbkdf2:sha256"), formacao='F')
        db.session.add(user)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def test_password_reset_flow(client, app):
    resp = client.post('/esqueci_senha_cpf', data={
        'acao': 'validar_cpf',
        'cpf': '123',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'nova_senha' in resp.data

    resp = client.post('/esqueci_senha_cpf', data={
        'acao': 'alterar_senha',
        'cpf': '123',
        'nova_senha': 'short',
        'confirmar_senha': 'short'
    }, follow_redirects=True)
    assert b'requisitos' in resp.data

    resp = client.post('/esqueci_senha_cpf', data={
        'acao': 'alterar_senha',
        'cpf': '123',
        'nova_senha': 'Senha123!',
        'confirmar_senha': 'Senha123!'
    }, follow_redirects=True)
    assert resp.request.path == '/login'

    with app.app_context():
        user = Usuario.query.filter_by(cpf='123').first()
        assert user.verificar_senha('Senha123!')
