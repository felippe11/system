import sys
import types
import pytest
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

# Stubs to avoid optional deps
mercadopago_stub = types.ModuleType('mercadopago')
mercadopago_stub.SDK = lambda *a, **k: None
sys.modules.setdefault('mercadopago', mercadopago_stub)
utils_stub = types.ModuleType('utils')
taxa_service = types.ModuleType('utils.taxa_service')
taxa_service.calcular_taxa_cliente = lambda *a, **k: {'taxa_aplicada': 0, 'usando_taxa_diferenciada': False}
taxa_service.calcular_taxas_clientes = lambda *a, **k: []
utils_stub.taxa_service = taxa_service
sys.modules.setdefault('utils', utils_stub)
sys.modules.setdefault('utils.taxa_service', taxa_service)

from app import create_app
from extensions import db, login_manager
from models import Usuario, Cliente, ReviewerApplication
from routes.auth_routes import auth_routes

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123'))
        admin = Usuario(nome='Admin', cpf='1', email='admin@test', senha=generate_password_hash('123'), formacao='x', tipo='admin')
        user = Usuario(nome='User', cpf='2', email='user@test', senha=generate_password_hash('123'), formacao='x')
        db.session.add_all([cliente, admin, user])
        db.session.commit()
        db.session.add(ReviewerApplication(usuario_id=user.id))
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_dashboard_applications_visible_for_cliente(client, app):
    login(client, 'cli@test', '123')
    resp = client.get('/dashboard_cliente')
    assert resp.status_code == 200
    assert b'User' in resp.data


def test_update_application_requires_permission(client, app):
    with app.app_context():
        rid = ReviewerApplication.query.first().id

    login(client, 'user@test', '123')
    resp = client.post(f'/reviewer_applications/{rid}', data={'action': 'advance'}, follow_redirects=True)
    assert b'dashboard' in resp.data
    with app.app_context():
        assert ReviewerApplication.query.get(rid).stage == 'novo'

    login(client, 'cli@test', '123')
    resp = client.post(f'/reviewer_applications/{rid}', data={'action': 'advance'}, follow_redirects=True)
    assert resp.status_code in (200, 302)
    with app.app_context():
        assert ReviewerApplication.query.get(rid).stage == 'triagem'
