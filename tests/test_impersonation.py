import pytest
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models.user import Usuario, Cliente

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        admin = Usuario(nome='Admin', cpf='1', email='admin@test', senha=generate_password_hash('123'), formacao='x', tipo='admin')
        db.session.add(admin)
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('456'))
        db.session.add(cliente)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_impersonation_flow(client, app):
    with app.app_context():
        cid = Cliente.query.first().id
    login(client, 'admin@test', '123')
    resp = client.get(f'/login_as_cliente/{cid}', follow_redirects=True)
    assert resp.status_code in (200, 302)
    with client.session_transaction() as sess:
        assert sess.get('user_type') == 'cliente'
        assert sess.get('impersonator_id') is not None
    resp = client.get('/encerrar_impersonacao', follow_redirects=True)
    assert resp.status_code in (200, 302)
    with client.session_transaction() as sess:
        assert sess.get('user_type') == 'admin'
        assert sess.get('impersonator_id') is None
