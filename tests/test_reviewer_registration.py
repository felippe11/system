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
from extensions import db
from models.user import Usuario, Cliente
from models.review import ReviewerApplication

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
    return app

@pytest.fixture
def client(app):
    return app.test_client()


def test_reviewer_registration_flow(client, app):
    resp = client.get('/peer-review/register')
    assert resp.status_code == 200

    data = {
        'nome': 'Rev',
        'cpf': '1',
        'email': 'rev@test',
        'formacao': 'x',
        'senha': '123'
    }
    resp = client.post('/peer-review/register', data=data, follow_redirects=False)
    assert resp.status_code in (302, 200)

    with app.app_context():
        user = Usuario.query.filter_by(email='rev@test').first()
        assert user is not None
        app_obj = ReviewerApplication.query.filter_by(usuario_id=user.id).first()
        assert app_obj is not None
