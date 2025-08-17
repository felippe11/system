from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
import os

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')

import utils
from models.user import Usuario, PasswordResetToken
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
        user = Usuario(nome='User', cpf='123', email='user@test', senha=generate_password_hash('123'), formacao='F')
        db.session.add(user)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def test_password_reset_flow(client, app, monkeypatch):
    sent = {}

    def fake_send(destinatario, nome_participante, nome_oficina, assunto, corpo_texto,
                  anexo_path=None, corpo_html=None):
        sent['dest'] = destinatario
        sent['assunto'] = assunto
        sent['body'] = corpo_texto

    monkeypatch.setattr('routes.auth_routes.enviar_email', fake_send)
    monkeypatch.setattr('requests.post',
                       lambda *a, **k: type('obj', (), {'json': lambda: {'success': True, 'score': 1}}))

    client.post('/esqueci_senha_cpf', data={'cpf': '123', 'g-recaptcha-response': 'dummy'}, follow_redirects=True)
    assert 'body' in sent
    assert 'token=' in sent['body']
    token = sent['body'].split('token=')[1].strip()

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
