import pytest
import os

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('DB_PASS', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db, login_manager
from models.user import Cliente, Monitor
from models.material import Polo, MonitorPolo


@pytest.fixture
def app():
    app = create_app()
    login_manager.session_protection = None
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options(
        app.config['SQLALCHEMY_DATABASE_URI']
    )
    with app.app_context():
        db.create_all()

        cliente = Cliente(nome='Cliente', email='c@test', senha='x')
        db.session.add(cliente)
        db.session.commit()

        polo_a = Polo(nome='Polo A', cliente_id=cliente.id, ativo=True)
        polo_b = Polo(nome='Polo B', cliente_id=cliente.id, ativo=True)
        db.session.add_all([polo_a, polo_b])
        db.session.commit()

        monitor_linked = Monitor(
            nome_completo='Monitor Ligado',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda',
            turnos_disponibilidade='manha',
            email='ml@test',
            telefone_whatsapp='1',
            codigo_acesso='XYZ123',
        )
        monitor_unlinked = Monitor(
            nome_completo='Monitor Solto',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda',
            turnos_disponibilidade='manha',
            email='mu@test',
            telefone_whatsapp='2',
            codigo_acesso='NOP456',
        )
        db.session.add_all([monitor_linked, monitor_unlinked])
        db.session.commit()

        atribuicao = MonitorPolo(
            monitor_id=monitor_linked.id,
            polo_id=polo_a.id,
            ativo=True,
        )
        db.session.add(atribuicao)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login_monitor_session(client, monitor_id):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(monitor_id)
        sess['_fresh'] = True
        sess['_id'] = 'test-session'
        sess['user_type'] = 'monitor'


def test_monitor_polos_assigned_only(client, app):
    with app.app_context():
        monitor = Monitor.query.filter_by(email='ml@test').first()
    with client:
        login_monitor_session(client, monitor.id)
        resp = client.get('/api/polos')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert [p['nome'] for p in data['polos']] == ['Polo A']


def test_monitor_polos_unassigned_empty(client, app):
    with app.app_context():
        monitor = Monitor.query.filter_by(email='mu@test').first()
    with client:
        login_monitor_session(client, monitor.id)
        resp = client.get('/api/polos')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert data['polos'] == []
