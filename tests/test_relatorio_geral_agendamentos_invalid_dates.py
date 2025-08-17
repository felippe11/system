import os
import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
os.environ.setdefault('SECRET_KEY', 'test')

from config import Config
from app import create_app
from extensions import db
from models.user import Cliente


Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)


@pytest.fixture
def app():
    os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
    os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
    os.environ.setdefault('SECRET_KEY', 'test')

    import sys
    sys.modules.pop('routes.agendamento_routes', None)
    sys.modules.pop('routes.dashboard_routes', None)
    app = create_app()
    if 'dashboard_routes.dashboard_cliente' not in app.view_functions:
        app.add_url_rule(
            '/dashboard_cliente',
            endpoint='dashboard_routes.dashboard_cliente',
            view_func=lambda: ''
        )
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome='Cli',
            email='cli@test',
            senha=generate_password_hash('123'),
        )
        db.session.add(cliente)
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post('/login', data={'email': 'cli@test', 'senha': '123'})


def test_invalid_start_date_defaults(client):
    login(client)
    resp = client.get('/relatorio_geral_agendamentos?data_inicio=bad-date', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Data inicial inv' in resp.data


def test_invalid_end_date_defaults(client):
    login(client)
    resp = client.get('/relatorio_geral_agendamentos?data_fim=bad-date', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Data final inv' in resp.data
