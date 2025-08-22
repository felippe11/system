import sys
import types
import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

# Stub utils package to avoid heavy optional dependencies during tests
utils_stub = types.ModuleType('utils')
taxa_service = types.ModuleType('utils.taxa_service')
taxa_service.calcular_taxa_cliente = lambda *a, **k: {
    'taxa_aplicada': 0,
    'usando_taxa_diferenciada': False
}
taxa_service.calcular_taxas_clientes = lambda *a, **k: []
utils_stub.taxa_service = taxa_service
utils_stub.brasilia_filter = lambda dt=None: 'now'
utils_stub.external_url = lambda *a, **k: '/url'
utils_stub.determinar_turno = lambda *a, **k: 'Manha'
sys.modules.setdefault('utils', utils_stub)
sys.modules.setdefault('utils.taxa_service', taxa_service)
# Stub qrcode module used in services
qrcode_stub = types.ModuleType('qrcode')
qrcode_stub.make = lambda *a, **k: None
sys.modules.setdefault('qrcode', qrcode_stub)

from flask import Flask
from extensions import db, login_manager
from models.user import Usuario, Cliente
from routes.auth_routes import auth_routes
from routes.dashboard_routes import dashboard_routes
from flask import Blueprint

evento_routes = Blueprint('evento_routes', __name__)

@evento_routes.route('/')
def home():
    return 'home'


@pytest.fixture
def app():
    app = Flask(__name__, template_folder='../templates')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options('sqlite://')
    app.secret_key = 'test'

    login_manager.init_app(app)
    db.init_app(app)

    app.register_blueprint(auth_routes)
    app.register_blueprint(dashboard_routes)
    app.register_blueprint(evento_routes)

    with app.app_context():
        db.create_all()
        superadmin = Usuario(
            nome='Super',
            cpf='1',
            email='super@test',
            senha=generate_password_hash('123', method="pbkdf2:sha256"),
            formacao='X',
            tipo='superadmin'
        )
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('456', method="pbkdf2:sha256"))
        db.session.add_all([superadmin, cliente])
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_superadmin_login_and_dashboard(client):
    import routes.dashboard_routes as dr
    dr.render_template = lambda *a, **k: 'ok'
    resp = client.post('/login', data={'email': 'super@test', 'senha': '123'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'ok' in resp.data
    resp = client.get('/dashboard_superadmin')
    assert resp.status_code == 200
