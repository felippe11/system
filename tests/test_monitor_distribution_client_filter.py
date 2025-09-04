import os
import pytest
from datetime import datetime, timedelta, time

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('DB_PASS', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db, login_manager
from models.user import Cliente, Monitor
from models.event import Evento, HorarioVisitacao, AgendamentoVisita, MonitorAgendamento


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

        c1 = Cliente(nome='Cliente1', email='c1@test', senha='x')
        c2 = Cliente(nome='Cliente2', email='c2@test', senha='x')
        db.session.add_all([c1, c2])
        db.session.flush()

        e1 = Evento(cliente_id=c1.id, nome='E1')
        e2 = Evento(cliente_id=c2.id, nome='E2')
        db.session.add_all([e1, e2])
        db.session.flush()

        d = datetime.utcnow().date() + timedelta(days=1)
        hv1 = HorarioVisitacao(
            evento_id=e1.id,
            data=d,
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
        )
        hv2 = HorarioVisitacao(
            evento_id=e2.id,
            data=d,
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
        )
        db.session.add_all([hv1, hv2])
        db.session.flush()

        ag1 = AgendamentoVisita(
            horario_id=hv1.id,
            cliente_id=c1.id,
            escola_nome='Escola1',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=10,
            status='confirmado',
        )
        ag2 = AgendamentoVisita(
            horario_id=hv2.id,
            cliente_id=c2.id,
            escola_nome='Escola2',
            turma='T2',
            nivel_ensino='Fundamental',
            quantidade_alunos=10,
            status='confirmado',
        )
        db.session.add_all([ag1, ag2])

        m1 = Monitor(
            nome_completo='Monitor1',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda',
            turnos_disponibilidade='manha',
            email='m1@test',
            telefone_whatsapp='1',
            codigo_acesso='AAA111',
            cliente_id=c1.id,
        )
        m2 = Monitor(
            nome_completo='Monitor2',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda',
            turnos_disponibilidade='manha',
            email='m2@test',
            telefone_whatsapp='2',
            codigo_acesso='BBB222',
            cliente_id=c2.id,
        )
        db.session.add_all([m1, m2])
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login_client_session(client, cliente_id):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_id)
        sess['_fresh'] = True
        sess['_id'] = 'test-session'
        sess['user_type'] = 'cliente'


def extract_stats(html):
    import re

    matches = re.findall(
        r"<h4>(\d+)</h4>\s*<p class=\"mb-0\">(Agendamentos sem Monitor|Monitores Ativos)</p>",
        html,
    )
    return {label: int(num) for num, label in matches}


def test_client_statistics_and_distribution_isolated(client, app):
    with app.app_context():
        c1 = Cliente.query.filter_by(email='c1@test').first()
        c2 = Cliente.query.filter_by(email='c2@test').first()
        ag1 = AgendamentoVisita.query.filter_by(cliente_id=c1.id).first()
        ag2 = AgendamentoVisita.query.filter_by(cliente_id=c2.id).first()
        m1 = Monitor.query.filter_by(cliente_id=c1.id).first()
        m2 = Monitor.query.filter_by(cliente_id=c2.id).first()

    # Cliente 1 statistics
    with client:
        login_client_session(client, c1.id)
        resp = client.get('/distribuicao-automatica')
        assert resp.status_code == 200
        stats = extract_stats(resp.data.decode())
        assert stats.get('Agendamentos sem Monitor') == 1
        assert stats.get('Monitores Ativos') == 1

        # Distribuição
        resp = client.post('/distribuir-automaticamente', json={'modo': 'somente_sem_monitor'})
        data = resp.get_json()
        assert data['success'] is True
        assert data['atribuicoes'] == 1
        detalhes = data.get('atribuicoes_detalhes', [])
        assert all(d['monitor_id'] == m1.id for d in detalhes)
        assert all(d['agendamento_id'] == ag1.id for d in detalhes)

    with app.app_context():
        assert (
            MonitorAgendamento.query.filter_by(monitor_id=m1.id, agendamento_id=ag1.id).count()
            == 1
        )
        assert (
            MonitorAgendamento.query.filter_by(agendamento_id=ag2.id).count() == 0
        )

    # Cliente 2 statistics and distribution
    with client:
        login_client_session(client, c2.id)
        resp = client.get('/distribuicao-automatica')
        assert resp.status_code == 200
        stats = extract_stats(resp.data.decode())
        assert stats.get('Agendamentos sem Monitor') == 1
        assert stats.get('Monitores Ativos') == 1

        resp = client.post('/distribuir-automaticamente', json={'modo': 'somente_sem_monitor'})
        data = resp.get_json()
        assert data['success'] is True
        assert data['atribuicoes'] == 1
        detalhes = data.get('atribuicoes_detalhes', [])
        assert all(d['monitor_id'] == m2.id for d in detalhes)
        assert all(d['agendamento_id'] == ag2.id for d in detalhes)

    with app.app_context():
        assert (
            MonitorAgendamento.query.filter_by(monitor_id=m2.id, agendamento_id=ag2.id).count()
            == 1
        )
        # Ensure no cross assignments
        assert (
            MonitorAgendamento.query.filter_by(monitor_id=m2.id, agendamento_id=ag1.id).count()
            == 0
        )
