import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Evento, Inscricao
from models.user import Cliente, Usuario, LinkCadastro


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'

    with app.app_context():
        db.create_all()

        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123', method="pbkdf2:sha256"))
        db.session.add(cliente)
        db.session.commit()

        evento1 = Evento(cliente_id=cliente.id, nome='E1', habilitar_lotes=False, inscricao_gratuita=True)
        evento2 = Evento(cliente_id=cliente.id, nome='E2', habilitar_lotes=False, inscricao_gratuita=True)
        db.session.add_all([evento1, evento2])
        db.session.commit()

        link1 = LinkCadastro(cliente_id=cliente.id, evento_id=evento1.id, token='t1')
        link2 = LinkCadastro(cliente_id=cliente.id, evento_id=evento2.id, token='t2')
        db.session.add_all([link1, link2])
        db.session.commit()

        usuario = Usuario(
            nome='User',
            cpf='111',
            email='user@example.com',
            senha=generate_password_hash('123', method="pbkdf2:sha256"),
            formacao='F',
            tipo='participante',
            cliente_id=cliente.id,
            evento_id=evento1.id,
        )
        db.session.add(usuario)
        db.session.commit()

        inscr = Inscricao(usuario_id=usuario.id, evento_id=evento1.id, cliente_id=cliente.id, status_pagamento='approved')
        db.session.add(inscr)
        db.session.commit()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_existing_user_registers_new_event(client, app):
    data = {
        'nome': 'User',
        'cpf': '111',
        'email': 'user@example.com',
        'senha': '123',
        'formacao': 'F',
    }

    resp = client.post('/inscricao/token/t2', data=data, follow_redirects=True)
    assert resp.status_code in (200, 302)

    with app.app_context():
        usuario = Usuario.query.filter_by(email='user@example.com').first()
        evento1 = Evento.query.filter_by(nome='E1').first()
        evento2 = Evento.query.filter_by(nome='E2').first()
        assert Usuario.query.count() == 1
        assert Inscricao.query.filter_by(usuario_id=usuario.id, evento_id=evento1.id).count() == 1
        assert Inscricao.query.filter_by(usuario_id=usuario.id, evento_id=evento2.id).count() == 1
        assert Inscricao.query.count() == 2


def test_existing_user_wrong_password_fails(client, app):
    data = {
        'nome': 'User',
        'cpf': '111',
        'email': 'user@example.com',
        'senha': 'wrong',
        'formacao': 'F',
    }

    resp = client.post('/inscricao/token/t2', data=data, follow_redirects=True)
    assert resp.status_code in (200, 302)
    assert b'Login AppFiber' in resp.data

    with app.app_context():
        usuario = Usuario.query.filter_by(email='user@example.com').first()
        evento2 = Evento.query.filter_by(nome='E2').first()
        assert Usuario.query.count() == 1
        assert Inscricao.query.filter_by(usuario_id=usuario.id, evento_id=evento2.id).count() == 0
        assert Inscricao.query.count() == 1
