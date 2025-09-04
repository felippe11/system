import os

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
os.environ.setdefault('DB_PASS', 'test')

import pytest
from unittest.mock import patch
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import Evento
from models.user import Usuario, Cliente
from models.certificado import SolicitacaoCertificado


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post(
        '/login',
        data={'email': email, 'senha': senha},
        follow_redirects=True,
    )


def setup_user_event():
    cliente = Cliente(
        nome='Cli',
        email='cli@example.com',
        senha=generate_password_hash('123', method='pbkdf2:sha256'),
    )
    db.session.add(cliente)
    db.session.commit()
    evento = Evento(cliente_id=cliente.id, nome='Evento')
    db.session.add(evento)
    usuario = Usuario(
        nome='User',
        cpf='1',
        email='user@example.com',
        senha=generate_password_hash('123', method='pbkdf2:sha256'),
        formacao='x',
        cliente_id=cliente.id,
    )
    db.session.add(usuario)
    db.session.commit()
    return cliente, evento, usuario


def test_solicitar_declaracao_duplicada(client, app):
    with app.app_context():
        _, evento, usuario = setup_user_event()
        solicitacao = SolicitacaoCertificado(
            usuario_id=usuario.id,
            evento_id=evento.id,
            tipo_certificado='declaracao',
            status='pendente',
        )
        db.session.add(solicitacao)
        db.session.commit()
        evento_id = evento.id
        email = usuario.email
    login(client, email, '123')
    resp = client.post('/solicitar_declaracao', json={'evento_id': evento_id})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['success'] is False
    with app.app_context():
        assert SolicitacaoCertificado.query.count() == 1


def test_solicitar_declaracao_sucesso(client, app):
    with app.app_context():
        _, evento, usuario = setup_user_event()
        evento_id = evento.id
        usuario_id = usuario.id
        email = usuario.email
    login(client, email, '123')
    with patch('routes.certificado_routes.criar_notificacao_solicitacao'):
        resp = client.post('/solicitar_declaracao', json={'evento_id': evento_id})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    with app.app_context():
        query = SolicitacaoCertificado.query.filter_by(
            usuario_id=usuario_id,
            evento_id=evento_id,
        )
        assert query.count() == 1
