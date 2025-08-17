import pytest
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import Evento, EventoInscricaoTipo, Inscricao
from models.user import Usuario, Cliente

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        admin = Usuario(nome='Admin', cpf='1', email='a@a', senha='x', formacao='x', tipo='admin')
        db.session.add(admin)
        cliente = Cliente(nome='C', email='c@c', senha='1')
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome='Pago', habilitar_lotes=False, inscricao_gratuita=False)
        db.session.add(evento)
        db.session.commit()
        tipo = EventoInscricaoTipo(evento_id=evento.id, nome='P', preco=10.0)
        db.session.add(tipo)
        db.session.commit()
        user = Usuario(nome='U', cpf='2', email='u@u', senha='x', formacao='x', tipo='participante', cliente_id=cliente.id)
        db.session.add(user)
        db.session.commit()
        insc = Inscricao(usuario_id=user.id, evento_id=evento.id, cliente_id=cliente.id, tipo_inscricao_id=tipo.id, status_pagamento='approved')
        db.session.add(insc)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_dashboard_admin_financeiro(client):
    resp = client.get('/dashboard_admin')
    assert resp.status_code == 200
    assert b'Resumo Financeiro por Cliente' in resp.data
