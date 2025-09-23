import os

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
os.environ.setdefault('DB_PASS', 'postgres')

import pytest
from werkzeug.security import generate_password_hash
from config import Config
from app import create_app
from extensions import db
from models.user import Cliente
from models.material import Polo, Material


@pytest.fixture
def app():
    Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
    Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
        Config.SQLALCHEMY_DATABASE_URI
    )
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome='Cli',
            email='cli@test',
            senha=generate_password_hash('123', method="pbkdf2:sha256"),
        )
        polo = Polo(nome='Polo', cliente=cliente)
        material = Material(
            nome='Caneta',
            unidade='unidade',
            quantidade_atual=10,
            quantidade_minima=5,
            polo=polo,
            cliente=cliente,
        )
        material.preco_unitario = 1
        db.session.add_all([cliente, polo, material])
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_excel_report_route(client):
    login(client, 'cli@test', '123')
    resp = client.get('/relatorios/materiais/excel')
    assert resp.status_code == 200
    assert (
        resp.mimetype
        == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


def test_json_report_route(client):
    login(client, 'cli@test', '123')
    resp = client.get('/api/materiais/relatorio')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert isinstance(data['materiais'], list)
