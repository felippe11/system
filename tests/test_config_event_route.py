import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Evento, ConfiguracaoCliente
from models.user import Cliente

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


def test_configuracao_evento_defaults(client, app):
    with app.app_context():
        cliente = Cliente(nome='Cli', email='cli@example.com', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome='EV')
        db.session.add(evento)
        db.session.commit()
        eid = evento.id
        db.session.add(ConfiguracaoCliente(cliente_id=cliente.id))
        db.session.commit()

    login(client, 'cli@example.com', '123')
    resp = client.get(f'/api/configuracao_evento/{eid}')
    assert resp.status_code == 200
    data = resp.get_json()
    expected_keys = [
        'permitir_checkin_global',
        'habilitar_qrcode_evento_credenciamento',
        'habilitar_feedback',
        'habilitar_certificado_individual',
        'mostrar_taxa',
        'habilitar_submissao_trabalhos',
        'review_model',
        'num_revisores_min',
        'num_revisores_max',
        'prazo_parecer_dias',
        'obrigatorio_nome',
        'obrigatorio_cpf',
        'obrigatorio_email',
        'obrigatorio_senha',
        'obrigatorio_formacao',
        'allowed_file_types',
    ]
    for key in expected_keys:
        assert key in data
    assert data['success'] is True
