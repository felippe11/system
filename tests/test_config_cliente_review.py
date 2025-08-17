import pytest
import os
os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import ConfiguracaoCliente, Evento, Formulario
from models.user import Cliente
from models.review import RevisaoConfig

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@example.com', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        db.session.add(ConfiguracaoCliente(cliente_id=cliente.id))
        evento = Evento(cliente_id=cliente.id, nome='Evento')
        db.session.add(evento)
        db.session.commit()
        db.session.add(RevisaoConfig(evento_id=evento.id))
        formulario = Formulario(
            cliente_id=cliente.id,
            nome='Form Sub',
            descricao='Desc',
            is_submission_form=True,
        )
        db.session.add(formulario)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_update_review_settings(client, app):
    login(client, 'cli@example.com', '123')
    resp = client.post('/set_review_model', json={'review_model': 'double'})
    assert resp.status_code == 200
    assert resp.get_json()['success']

    resp = client.post('/set_num_revisores_min', json={'value': 2})
    assert resp.status_code == 200
    resp = client.post('/set_num_revisores_max', json={'value': 3})
    assert resp.status_code == 200
    resp = client.post('/set_prazo_parecer_dias', json={'value': 10})
    assert resp.status_code == 200
    resp = client.post('/set_max_trabalhos_revisor', json={'value': 7})
    assert resp.status_code == 200

    with app.app_context():
        config = ConfiguracaoCliente.query.first()
        assert config.review_model == 'double'
        assert config.num_revisores_min == 2
        assert config.num_revisores_max == 3
        assert config.prazo_parecer_dias == 10
        assert config.allowed_file_types == 'pdf'
        assert config.max_trabalhos_por_revisor == 7


def test_dashboard_defaults(client, app):
    login(client, 'cli@example.com', '123')
    resp = client.get('/config_submissao')
    assert resp.status_code == 200
    assert b'value="single"' in resp.data
    assert b'id="inputRevisoresMin" value="1"' in resp.data
    assert b'id="inputRevisoresMax" value="2"' in resp.data
    assert b'id="inputPrazoParecer" value="14"' in resp.data
    assert b'id="inputMaxTrabalhosRevisor" value="5"' in resp.data
    assert b'id="inputAllowedFiles"' in resp.data
    assert b'id="selectFormularioSubmissao"' in resp.data
    assert b'Form Sub' in resp.data


def test_set_formulario_submissao(client, app):
    login(client, 'cli@example.com', '123')
    with app.app_context():
        formulario_id = Formulario.query.first().id
    resp = client.post('/set_formulario_submissao', json={'formulario_id': formulario_id})
    assert resp.status_code == 200
    assert resp.get_json()['success']
    with app.app_context():
        config = ConfiguracaoCliente.query.first()
        assert config.formulario_submissao_id == formulario_id


def test_revisao_config_update_and_interface(client, app):
    login(client, 'cli@example.com', '123')
    with app.app_context():
        evento_id = Evento.query.first().id
    payload = {
        'numero_revisores': 3,
        'prazo_revisao': '2030-01-02T00:00:00',
        'modelo_blind': 'double',
    }
    resp = client.post(f'/revisao_config/{evento_id}', json=payload)
    assert resp.status_code == 200
    assert resp.get_json()['success']

    with app.app_context():
        cfg = RevisaoConfig.query.filter_by(evento_id=evento_id).first()
        assert cfg.numero_revisores == 3
        assert cfg.prazo_revisao.isoformat().startswith('2030-01-02')
        assert cfg.modelo_blind == 'double'

    resp = client.get('/config_submissao')
    assert resp.status_code == 200
    assert b'id="inputNumeroRevisores"' in resp.data
    assert b'id="inputPrazoRevisao"' in resp.data
    assert b'id="selectModeloBlind"' in resp.data
    assert b'"numero_revisores": 3' in resp.data
    assert b'"modelo_blind": "double"' in resp.data
