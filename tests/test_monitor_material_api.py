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
from models.material import Polo, Material, MonitorPolo


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

        cliente1 = Cliente(nome='Cliente', email='c@test', senha='x')
        cliente2 = Cliente(nome='Outro', email='o@test', senha='x')
        db.session.add_all([cliente1, cliente2])
        db.session.commit()

        polo_a = Polo(nome='Polo A', cliente_id=cliente1.id, ativo=True)
        polo_b = Polo(nome='Polo B', cliente_id=cliente1.id, ativo=True)
        polo_c = Polo(nome='Polo C', cliente_id=cliente2.id, ativo=True)
        db.session.add_all([polo_a, polo_b, polo_c])
        db.session.commit()

        mat_a = Material(
            nome='Material A',
            polo_id=polo_a.id,
            cliente_id=cliente1.id,
            quantidade_inicial=1,
            quantidade_atual=1,
            quantidade_minima=0,
        )
        mat_b = Material(
            nome='Material B',
            polo_id=polo_b.id,
            cliente_id=cliente1.id,
            quantidade_inicial=1,
            quantidade_atual=1,
            quantidade_minima=0,
        )
        mat_c = Material(
            nome='Material C',
            polo_id=polo_c.id,
            cliente_id=cliente2.id,
            quantidade_inicial=1,
            quantidade_atual=1,
            quantidade_minima=0,
        )
        db.session.add_all([mat_a, mat_b, mat_c])
        db.session.commit()

        monitor1 = Monitor(
            nome_completo='Monitor Um',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda',
            turnos_disponibilidade='manha',
            email='m1@test',
            telefone_whatsapp='1',
            codigo_acesso='ABC123',
            cliente_id=cliente1.id,
        )
        monitor2 = Monitor(
            nome_completo='Monitor Dois',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda',
            turnos_disponibilidade='manha',
            email='m2@test',
            telefone_whatsapp='2',
            codigo_acesso='DEF456',
            cliente_id=cliente1.id,
        )
        db.session.add_all([monitor1, monitor2])
        db.session.commit()

        atribuicao1 = MonitorPolo(
            monitor_id=monitor1.id,
            polo_id=polo_a.id,
            ativo=True,
        )
        atribuicao2 = MonitorPolo(
            monitor_id=monitor1.id,
            polo_id=polo_c.id,
            ativo=True,
        )
        db.session.add_all([atribuicao1, atribuicao2])
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

def test_monitor_with_assignments(client, app):
    with app.app_context():
        monitor = Monitor.query.filter_by(email='m1@test').first()

    with client:
        login_monitor_session(client, monitor.id)
        resp = client.get('/api/materiais')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert len(data['materiais']) == 1
        assert data['materiais'][0]['nome'] == 'Material A'
        assert 'Material C' not in [m['nome'] for m in data['materiais']]


def test_monitor_without_assignments(client, app):
    with app.app_context():
        monitor = Monitor.query.filter_by(email='m2@test').first()

    with client:
        login_monitor_session(client, monitor.id)
        resp = client.get('/api/materiais')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert data['materiais'] == []
