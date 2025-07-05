import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Cliente, Evento, Formulario

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        form = Formulario(nome='F1', cliente_id=cliente.id)
        ev1 = Evento(cliente_id=cliente.id, nome='E1', inscricao_gratuita=True, publico=True)
        ev2 = Evento(cliente_id=cliente.id, nome='E2', inscricao_gratuita=True, publico=True)
        db.session.add_all([form, ev1, ev2])
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_atribuir_eventos(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        form = Formulario.query.first()
        ev1 = Evento.query.filter_by(nome='E1').first()
        ev2 = Evento.query.filter_by(nome='E2').first()

    login(client, 'cli@test', '123')
    resp = client.post(f'/formularios/{form.id}/eventos', data={'eventos': [ev1.id, ev2.id]}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        form = Formulario.query.get(form.id)
        assert {e.id for e in form.eventos} == {ev1.id, ev2.id}
