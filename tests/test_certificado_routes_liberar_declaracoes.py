import os
from datetime import datetime

import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
os.environ.setdefault('DB_PASS', 'test')

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

import models.formulario as formulario_module
from app import create_app
from extensions import db
from models import Evento, Checkin, DeclaracaoComparecimento
from models.user import Usuario, Cliente
from models.certificado import DeclaracaoTemplate
import utils.auth as auth


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(
        formulario_module, 'ensure_formulario_trabalhos', lambda: None
    )
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


def setup_entities(create_template=True):
    cliente = Cliente(
        nome='Cli',
        email='cli@example.com',
        senha=generate_password_hash('123', method='pbkdf2:sha256'),
    )
    db.session.add(cliente)
    db.session.commit()

    evento = Evento(
        cliente_id=cliente.id,
        nome='Evento',
        data_inicio=datetime.now(),
    )
    db.session.add(evento)
    db.session.commit()

    usuario1 = Usuario(
        nome='User1',
        cpf='1',
        email='u1@example.com',
        senha=generate_password_hash('123', method='pbkdf2:sha256'),
        formacao='x',
        cliente_id=cliente.id,
    )
    usuario2 = Usuario(
        nome='User2',
        cpf='2',
        email='u2@example.com',
        senha=generate_password_hash('123', method='pbkdf2:sha256'),
        formacao='y',
        cliente_id=cliente.id,
    )
    db.session.add_all([usuario1, usuario2])
    db.session.commit()

    checkins = [
        Checkin(
            usuario_id=usuario1.id,
            evento_id=evento.id,
            palavra_chave='ok',
            cliente_id=cliente.id,
        ),
        Checkin(
            usuario_id=usuario2.id,
            evento_id=evento.id,
            palavra_chave='ok',
            cliente_id=cliente.id,
        ),
    ]
    db.session.add_all(checkins)

    template = None
    if create_template:
        template = DeclaracaoTemplate(
            cliente_id=cliente.id,
            nome='Temp',
            tipo='individual',
            conteudo='conteudo',
            ativo=True,
        )
        db.session.add(template)

    db.session.commit()

    return cliente, evento, template


def test_habilitar_liberacao_declaracoes_success(app, client, monkeypatch):
    with app.app_context():
        cliente, evento, template = setup_entities()
        evento_id = evento.id
        template_id = template.id

    monkeypatch.setattr(auth, 'has_permission', lambda *_, **__: True)

    login(client, cliente.email, '123')
    resp = client.post(
        '/declaracoes/habilitar-liberacao',
        json={'evento_id': evento_id, 'template_id': template_id},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    with app.app_context():
        declaracoes = DeclaracaoComparecimento.query.filter_by(
            evento_id=evento_id
        ).all()
        assert len(declaracoes) == 2
        assert all(d.status == 'liberada' for d in declaracoes)


def test_habilitar_liberacao_declaracoes_template_missing(app, client, monkeypatch):
    with app.app_context():
        cliente, evento, _ = setup_entities(create_template=False)
        evento_id = evento.id

    monkeypatch.setattr(auth, 'has_permission', lambda *_, **__: True)

    login(client, cliente.email, '123')
    resp = client.post(
        '/declaracoes/habilitar-liberacao',
        json={'evento_id': evento_id},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['success'] is False
    assert 'Template' in data['message']
    with app.app_context():
        assert DeclaracaoComparecimento.query.count() == 0
