import os
import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'test')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'test')

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import Cliente, Evento, Formulario, RevisorProcess


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
        ev1 = Evento(
            cliente_id=cliente.id,
            nome='E1',
            inscricao_gratuita=True,
            publico=True,
        )
        ev2 = Evento(
            cliente_id=cliente.id,
            nome='E2',
            inscricao_gratuita=True,
            publico=True,
        )
        db.session.add_all([ev1, ev2])
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
    with app.app_context():
        ev1 = Evento.query.filter_by(nome='E1').first()
        ev2 = Evento.query.filter_by(nome='E2').first()

    login(client, 'cli@test', '123')
    resp = client.post(
        '/formularios/novo',
        data={'nome': 'F1', 'vincular_processo': 'on', 'eventos': [ev1.id]},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        form = Formulario.query.filter_by(nome='F1').first()
        assert form is not None
        assert {e.id for e in form.eventos} == {ev1.id}
        assert ev2.id not in {e.id for e in form.eventos}
        proc = RevisorProcess.query.filter_by(cliente_id=form.cliente_id).first()
        assert proc is not None
        assert proc.formulario_id == form.id
        assert {e.id for e in proc.formulario.eventos} == {ev1.id}

