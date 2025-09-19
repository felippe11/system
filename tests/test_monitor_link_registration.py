import os
from datetime import datetime, timedelta

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('DB_PASS', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')

import pytest
from werkzeug.security import generate_password_hash
from config import Config
from app import create_app
from extensions import db
from models.user import Cliente, MonitorCadastroLink, Monitor
import models  # noqa: F401


Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(
        'models.formulario.ensure_formulario_trabalhos',
        lambda: None,
    )
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options(
        app.config['SQLALCHEMY_DATABASE_URI']
    )
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome='Cli',
            email='c@test',
            senha=generate_password_hash('senha123'),
        )
        db.session.add(cliente)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login_cliente(client, cliente):
    client.post(
        '/login',
        data={'email': cliente.email, 'senha': 'senha123'},
        follow_redirects=True,
    )
    with client.session_transaction() as sess:
        sess['user_type'] = 'cliente'


def test_generate_link(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
    with client:
        login_cliente(client, cliente)
        expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        resp = client.post('/monitor/gerar_link', json={'expires_at': expires_at})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success']
        token = data['url'].rsplit('/', 1)[-1]
        with app.app_context():
            assert MonitorCadastroLink.query.filter_by(token=token).count() == 1


def test_register_with_valid_token(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        link = MonitorCadastroLink(
            cliente_id=cliente.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.session.add(link)
        db.session.commit()
        token = link.token

    resp = client.post(
        f'/monitor/inscricao/{token}',
        data={
            'nome_completo': 'Mon',
            'curso': 'C',
            'email': 'm@test',
            'telefone_whatsapp': '1',
            'carga_horaria_disponibilidade': '5',
            'dias_disponibilidade': 'segunda',
            'turnos_disponibilidade': 'manha',
        },
        follow_redirects=True,
    )
    assert resp.request.path == '/monitor/dashboard'
    with app.app_context():
        monitor = Monitor.query.filter_by(email='m@test').first()
        assert monitor is not None
        link = MonitorCadastroLink.query.filter_by(token=token).first()
        assert link is not None
        assert link.usage_count == 1
    with client.session_transaction() as sess:
        assert sess['user_type'] == 'monitor'


def test_reject_expired_token(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        link = MonitorCadastroLink(
            cliente_id=cliente.id,
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.session.add(link)
        db.session.commit()
        token = link.token

    resp = client.get(f'/monitor/inscricao/{token}')
    assert resp.status_code == 400


def test_reuse_before_expiration_and_reject_after(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        link = MonitorCadastroLink(
            cliente_id=cliente.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.session.add(link)
        db.session.commit()
        token = link.token

    client.post(
        f'/monitor/inscricao/{token}',
        data={
            'nome_completo': 'Mon',
            'curso': 'C',
            'email': 'unique@test',
            'telefone_whatsapp': '1',
            'carga_horaria_disponibilidade': '5',
            'dias_disponibilidade': 'segunda',
            'turnos_disponibilidade': 'manha',
        },
        follow_redirects=True,
    )
    with client.session_transaction() as sess:
        sess.clear()
    second_resp = client.post(
        f'/monitor/inscricao/{token}',
        data={
            'nome_completo': 'Outro',
            'curso': 'C2',
            'email': 'another@test',
            'telefone_whatsapp': '2',
            'carga_horaria_disponibilidade': '8',
            'dias_disponibilidade': 'terca',
            'turnos_disponibilidade': 'tarde',
        },
        follow_redirects=True,
    )
    assert second_resp.request.path == '/monitor/dashboard'
    with app.app_context():
        link = MonitorCadastroLink.query.filter_by(token=token).first()
        assert link is not None
        assert link.usage_count == 2
        link.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()

    with client.session_transaction() as sess:
        sess.clear()
    resp = client.get(f'/monitor/inscricao/{token}')
    assert resp.status_code == 400

