from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db, mail
from models import Usuario, PasswordResetToken
from werkzeug.security import generate_password_hash
import pytest
import os

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
        user = Usuario(nome='User', cpf='123', email='user@test', senha=generate_password_hash('123'), formacao='F')
        db.session.add(user)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def test_password_reset_flow(client, app, monkeypatch):
    sent = {}

    def fake_send(msg):
        sent['msg'] = msg

    monkeypatch.setattr(mail, 'send', fake_send)

    client.post('/esqueci_senha_cpf', data={'cpf': '123'}, follow_redirects=True)
    assert 'msg' in sent
    body = sent['msg'].body
    assert 'token=' in body
    token = body.split('token=')[1].strip()

    resp = client.post(f'/reset_senha_cpf?token={token}', data={
        'token': token,
        'nova_senha': 'short',
        'confirmar_senha': 'short'
    }, follow_redirects=True)
    assert b'requisitos' in resp.data

    resp = client.post(f'/reset_senha_cpf?token={token}', data={
        'token': token,
        'nova_senha': 'Senha123',
        'confirmar_senha': 'Senha123'
    }, follow_redirects=True)
    assert resp.request.path == '/login'

    with app.app_context():
        user = Usuario.query.filter_by(cpf='123').first()
        assert user.verificar_senha('Senha123')
        assert PasswordResetToken.query.filter_by(token=token, used=True).count() == 1
