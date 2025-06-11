import pytest
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = {}

from app import create_app
from extensions import db
from models import Cliente, Evento, EventoInscricaoTipo, LoteInscricao, LoteTipoInscricao, LinkCadastro

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()

        cliente = Cliente(nome='Cliente', email='c@example.com', senha='123')
        db.session.add(cliente)
        db.session.commit()

        evento = Evento(cliente_id=cliente.id, nome='Evento Teste', habilitar_lotes=True, inscricao_gratuita=False)
        db.session.add(evento)
        db.session.commit()

        tipo = EventoInscricaoTipo(evento_id=evento.id, nome='Pago', preco=20.0)
        db.session.add(tipo)
        db.session.commit()

        lote = LoteInscricao(evento_id=evento.id, nome='Lote 1')
        db.session.add(lote)
        db.session.commit()

        lt = LoteTipoInscricao(lote_id=lote.id, tipo_inscricao_id=tipo.id, preco=20.0)
        db.session.add(lt)
        db.session.commit()

        link = LinkCadastro(cliente_id=cliente.id, evento_id=evento.id, token='testtoken')
        db.session.add(link)
        db.session.commit()

    yield app

@pytest.fixture

def client(app):
    return app.test_client()

def test_get_inscricao_page(client):
    resp = client.get('/inscricao/token/testtoken')
    assert resp.status_code == 200
    assert b'Evento Teste' in resp.data

