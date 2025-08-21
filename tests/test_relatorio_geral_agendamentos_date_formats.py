import os
import pytest
import contextlib
from datetime import date
from flask import template_rendered
from werkzeug.security import generate_password_hash

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
os.environ.setdefault('SECRET_KEY', 'test')

from config import Config
from app import create_app
from extensions import db
from models.user import Cliente

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)


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


@contextlib.contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def test_accepts_iso_format(client, app):
    login(client)
    with captured_templates(app) as templates:
        resp = client.get(
            '/relatorio_geral_agendamentos?data_inicio=2024-01-01&data_fim=2024-12-31'
        )
    assert resp.status_code == 200
    template, context = templates[0]
    assert context['filtros']['data_inicio'] == date(2024, 1, 1)
    assert context['filtros']['data_fim'] == date(2024, 12, 31)


def test_accepts_br_format(client, app):
    login(client)
    with captured_templates(app) as templates:
        resp = client.get(
            '/relatorio_geral_agendamentos?data_inicio=01/01/2024&data_fim=31/12/2024'
        )
    assert resp.status_code == 200
    template, context = templates[0]
    assert context['filtros']['data_inicio'] == date(2024, 1, 1)
    assert context['filtros']['data_fim'] == date(2024, 12, 31)


def test_invalid_date_shows_message(client):
    login(client)
    resp = client.get(
        '/relatorio_geral_agendamentos?data_inicio=2024/01/01',
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert 'Formato de data inválido' in resp.get_data(as_text=True)
