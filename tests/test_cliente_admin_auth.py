import sys
import types
import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

# Stub utils package to avoid heavy dependencies
utils_stub = types.ModuleType('utils')
taxa_service = types.ModuleType('utils.taxa_service')
taxa_service.calcular_taxa_cliente = lambda *a, **k: {
    'taxa_aplicada': 0,
    'usando_taxa_diferenciada': False
}
taxa_service.calcular_taxas_clientes = lambda *a, **k: []
utils_stub.taxa_service = taxa_service
sys.modules.setdefault('utils', utils_stub)
sys.modules.setdefault('utils.taxa_service', taxa_service)

from flask import Flask
from extensions import db, login_manager
from models.user import Usuario, Cliente
from routes.auth_routes import auth_routes
from flask import Blueprint
from routes.dashboard_participante import dashboard_participante_routes

# Minimal dashboard blueprint for redirection target
dashboard_routes = Blueprint('dashboard_routes', __name__)

@dashboard_routes.route('/dashboard')
def dashboard():
    return 'dashboard'
from routes.cliente_routes import cliente_routes

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options('sqlite://')
    app.secret_key = 'test'

    login_manager.init_app(app)
    db.init_app(app)

    app.register_blueprint(auth_routes)
    app.register_blueprint(dashboard_routes)
    app.register_blueprint(dashboard_participante_routes)
    app.register_blueprint(cliente_routes)

    with app.app_context():
        db.create_all()
        admin = Usuario(nome='Admin', cpf='1', email='admin@test', senha=generate_password_hash('123', method="pbkdf2:sha256"), formacao='x', tipo='admin')
        user1 = Usuario(nome='User1', cpf='2', email='user@test', senha=generate_password_hash('123', method="pbkdf2:sha256"), formacao='y')
        user2 = Usuario(nome='User2', cpf='3', email='other@test', senha=generate_password_hash('123', method="pbkdf2:sha256"), formacao='z')
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('456', method="pbkdf2:sha256"))
        db.session.add_all([admin, user1, user2, cliente])
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=False)


def test_restringir_clientes_denied(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        cid = cliente.id
    login(client, 'user@test', '123')
    resp = client.post('/restringir_clientes', data={'cliente_ids': [cid]}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'dashboard' in resp.data
    with app.app_context():
        assert Cliente.query.get(cid).ativo == cliente.ativo


def test_excluir_clientes_denied(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        cid = cliente.id
    login(client, 'user@test', '123')
    resp = client.post('/excluir_clientes', data={'cliente_ids': [cid]}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'dashboard' in resp.data
    with app.app_context():
        assert Cliente.query.get(cid) is not None


def test_toggle_usuario_denied(client, app):
    with app.app_context():
        target_id = Usuario.query.filter_by(email='other@test').first().id
    login(client, 'user@test', '123')
    resp = client.get(f'/toggle_usuario/{target_id}', follow_redirects=True)
    assert resp.status_code == 200
    assert b'dashboard' in resp.data
    with app.app_context():
        assert Usuario.query.get(target_id).ativo is True
