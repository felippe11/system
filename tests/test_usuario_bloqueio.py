import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models.user import Usuario


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'

    with app.app_context():
        db.create_all()
        admin = Usuario(
            nome='Admin', cpf='1', email='admin@test',
            senha=generate_password_hash('123'), formacao='X', tipo='admin'
        )
        user = Usuario(
            nome='User', cpf='2', email='user@test',
            senha=generate_password_hash('123'), formacao='Y'
        )
        db.session.add_all([admin, user])
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_toggle_usuario_block_login(client, app):
    with app.app_context():
        user_id = Usuario.query.filter_by(email='user@test').first().id

    login(client, 'admin@test', '123')
    client.get(f'/toggle_usuario/{user_id}', follow_redirects=True)

    with app.app_context():
        assert Usuario.query.get(user_id).ativo is False

    resp = login(client, 'user@test', '123')
    assert b'Sua conta est' in resp.data
