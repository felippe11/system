import os
import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Evento, Formulario
from models.user import Cliente


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        c1 = Cliente(nome='C1', email='c1@test', senha=generate_password_hash('123'))
        c2 = Cliente(nome='C2', email='c2@test', senha=generate_password_hash('123'))
        db.session.add_all([c1, c2])
        db.session.commit()
        e1 = Evento(cliente_id=c1.id, nome='E1', inscricao_gratuita=True, publico=True)
        e2 = Evento(cliente_id=c2.id, nome='E2', inscricao_gratuita=True, publico=True)
        db.session.add_all([e1, e2])
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_vinculo_evento_outro_cliente_rejeitado(client, app):
    with app.app_context():
        evento_estranho = Evento.query.filter_by(nome='E2').first()
    login(client, 'c1@test', '123')
    resp = client.post(
        '/formularios/novo',
        data={'nome': 'FormX', 'eventos': [evento_estranho.id]},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert 'Evento inválido' in resp.get_data(as_text=True)
    with app.app_context():
        assert Formulario.query.count() == 0
