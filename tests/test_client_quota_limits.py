import pytest
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Evento, ConfiguracaoCliente, Formulario
from models.user import Cliente, Usuario

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
        db.session.add(ConfiguracaoCliente(cliente_id=cliente.id, limite_eventos=1, limite_formularios=1))
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_event_quota_enforced(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        cid = cliente.id
        Evento(cliente_id=cid, nome='EV1')
        db.session.commit()

    login(client, 'cli@test', '123')
    resp = client.post('/criar_evento', data={'nome': 'EV2', 'nome_tipo[]': 'P', 'preco_tipo[]': '0'}, follow_redirects=True)
    with app.app_context():
        assert Evento.query.filter_by(cliente_id=cid).count() == 1


def test_form_quota_enforced(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        cid = cliente.id
        Formulario(nome='F1', cliente_id=cid)
        db.session.commit()

    login(client, 'cli@test', '123')
    resp = client.post('/formularios/novo', data={'nome': 'F2'}, follow_redirects=True)
    with app.app_context():
        assert Formulario.query.filter_by(cliente_id=cid).count() == 1
