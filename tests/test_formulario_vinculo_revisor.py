import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import Formulario, Evento
from models.user import Cliente
from models.review import RevisorProcess


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome='Cli', email='cli@test', senha=generate_password_hash('123', method="pbkdf2:sha256")
        )
        db.session.add(cliente)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post(
        '/login', data={'email': email, 'senha': senha}, follow_redirects=True
    )


def test_form_creation_does_not_create_revisor_process(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        evento = Evento(
            cliente_id=cliente.id,
            nome='E1',
            inscricao_gratuita=True,
            publico=True,
        )
        db.session.add(evento)
        db.session.commit()
        evento_id = evento.id

    login(client, 'cli@test', '123')
    resp = client.post(
        '/formularios/novo',
        data={'nome': 'F1', 'eventos': [evento_id]},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        form = Formulario.query.filter_by(nome='F1').first()
        assert form is not None
        proc = RevisorProcess.query.filter_by(cliente_id=form.cliente_id).first()
        assert proc is None

