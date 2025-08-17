import pytest
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Evento, Oficina
from models.user import Cliente, Ministrante

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='C', email='c@c', senha='1')
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome='E', habilitar_lotes=False, inscricao_gratuita=True)
        db.session.add(evento)
        db.session.commit()
        ministrante = Ministrante(
            nome='M',
            formacao='x',
            categorias_formacao=None,
            foto=None,
            areas_atuacao='a',
            cpf='123',
            pix='1',
            cidade='C',
            estado='S',
            email='m@m',
            senha='x'
        )
        db.session.add(ministrante)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_oficina_init_inscricao_gratuita(app):
    with app.app_context():
        cliente = Cliente.query.first()
        evento = Evento.query.first()
        ministrante = Ministrante.query.first()
        of = Oficina(
            titulo='T',
            descricao='D',
            ministrante_id=ministrante.id,
            vagas=10,
            carga_horaria='2h',
            estado='SP',
            cidade='Sao Paulo',
            cliente_id=cliente.id,
            evento_id=evento.id,
            inscricao_gratuita=False,
        )
        db.session.add(of)
        db.session.commit()
        stored = Oficina.query.first()
        assert stored.inscricao_gratuita is False
