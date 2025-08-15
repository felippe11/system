import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import Cliente, Formulario, RevisorProcess, Evento


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome='Cli', email='cli@test', senha=generate_password_hash('123')
        )
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(
            cliente_id=cliente.id,
            nome='E1',
            inscricao_gratuita=True,
            publico=True,
        )
        db.session.add(evento)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post(
        '/login', data={'email': email, 'senha': senha}, follow_redirects=True
    )


def test_form_creation_links_revisor_process(client, app):
    login(client, 'cli@test', '123')
    with app.app_context():
        evento = Evento.query.first()
    resp = client.post(
        '/formularios/novo',
        data={'nome': 'F1', 'vincular_processo': 'on', 'eventos': str(evento.id)},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        form = Formulario.query.filter_by(nome='F1').first()
        assert form is not None
        proc = RevisorProcess.query.filter_by(cliente_id=form.cliente_id).first()
        assert proc is not None
        assert proc.formulario_id == form.id
        assert evento.id in [e.id for e in proc.eventos]

