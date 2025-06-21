import pytest
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)
from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models import Usuario, Cliente, CampoPersonalizadoCadastro

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_adicionar_campo_personalizado_unauthorized(client, app):
    with app.app_context():
        user = Usuario(nome='User', cpf='1', email='u@example.com', senha=generate_password_hash('123'), formacao='x')
        db.session.add(user)
        db.session.commit()

    login(client, 'u@example.com', '123')
    resp = client.post('/adicionar_campo_personalizado', data={'nome_campo': 'Campo', 'tipo_campo': 'texto', 'obrigatorio': 'on'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Acesso negado' in resp.data
    with app.app_context():
        assert CampoPersonalizadoCadastro.query.count() == 0


def test_remover_campo_personalizado_unauthorized(client, app):
    with app.app_context():
        cliente = Cliente(nome='Cli', email='c@example.com', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        campo = CampoPersonalizadoCadastro(cliente_id=cliente.id, nome='C', tipo='texto')
        user = Usuario(nome='User', cpf='2', email='user2@example.com', senha=generate_password_hash('123'), formacao='y')
        db.session.add_all([campo, user])
        db.session.commit()
        field_id = campo.id

    login(client, 'user2@example.com', '123')
    resp = client.post(f'/remover_campo_personalizado/{field_id}', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Acesso negado' in resp.data
    with app.app_context():
        assert CampoPersonalizadoCadastro.query.get(field_id) is not None
