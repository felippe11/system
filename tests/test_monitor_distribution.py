import os
from datetime import datetime, timedelta, time

import pytest

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
from models.event import (
    Evento,
    HorarioVisitacao,
    AgendamentoVisita,
    MonitorAgendamento,
)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(
        'models.formulario.ensure_formulario_trabalhos',
        lambda: None,
    )

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

        cliente1 = Cliente(nome='Cliente1', email='c1@test', senha='x')
        cliente2 = Cliente(nome='Cliente2', email='c2@test', senha='x')
        db.session.add_all([cliente1, cliente2])
        db.session.commit()

        evento1 = Evento(cliente_id=cliente1.id, nome='Evento1')
        evento2 = Evento(cliente_id=cliente2.id, nome='Evento2')
        db.session.add_all([evento1, evento2])
        db.session.commit()

        today = datetime.now().date()
        hv1a = HorarioVisitacao(
            evento_id=evento1.id,
            data=today + timedelta(days=1),
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
            fechado=False,
        )
        hv1b = HorarioVisitacao(
            evento_id=evento1.id,
            data=today + timedelta(days=2),
            horario_inicio=time(10, 0),
            horario_fim=time(11, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
            fechado=False,
        )
        hv2a = HorarioVisitacao(
            evento_id=evento2.id,
            data=today + timedelta(days=3),
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
            fechado=False,
        )
        hv2b = HorarioVisitacao(
            evento_id=evento2.id,
            data=today + timedelta(days=4),
            horario_inicio=time(10, 0),
            horario_fim=time(11, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
            fechado=False,
        )
        db.session.add_all([hv1a, hv1b, hv2a, hv2b])
        db.session.commit()

        monitor1 = Monitor(
            nome_completo='Monitor1',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda,terca,quarta,quinta,sexta,sabado,domingo',
            turnos_disponibilidade='manha',
            email='m1@test',
            telefone_whatsapp='1',
            codigo_acesso='AAA111',
            cliente_id=cliente1.id,
        )
        monitor2 = Monitor(
            nome_completo='Monitor2',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda,terca,quarta,quinta,sexta,sabado,domingo',
            turnos_disponibilidade='manha',
            email='m2@test',
            telefone_whatsapp='2',
            codigo_acesso='BBB222',
            cliente_id=cliente2.id,
        )
        monitor_global = Monitor(
            nome_completo='MonitorGlobal',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda,terca,quarta,quinta,sexta,sabado,domingo',
            turnos_disponibilidade='manha',
            email='mg@test',
            telefone_whatsapp='3',
            codigo_acesso='CCC333',
            cliente_id=None,
        )
        db.session.add_all([monitor1, monitor2, monitor_global])
        db.session.commit()

        ag1_sem = AgendamentoVisita(
            horario_id=hv1a.id,
            escola_nome='E1',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=10,
            qr_code_token='token1',
            cliente_id=cliente1.id,
        )
        ag2_sem = AgendamentoVisita(
            horario_id=hv2a.id,
            escola_nome='E2',
            turma='T2',
            nivel_ensino='Fundamental',
            quantidade_alunos=10,
            qr_code_token='token2',
            cliente_id=cliente2.id,
        )
        ag1_atr = AgendamentoVisita(
            horario_id=hv1b.id,
            escola_nome='E1',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=10,
            qr_code_token='token3',
            cliente_id=cliente1.id,
        )
        ag2_atr = AgendamentoVisita(
            horario_id=hv2b.id,
            escola_nome='E2',
            turma='T2',
            nivel_ensino='Fundamental',
            quantidade_alunos=10,
            qr_code_token='token4',
            cliente_id=cliente2.id,
        )
        db.session.add_all([ag1_sem, ag2_sem, ag1_atr, ag2_atr])
        db.session.commit()

        db.session.add_all([
            MonitorAgendamento(monitor_id=monitor1.id, agendamento_id=ag1_atr.id),
            MonitorAgendamento(monitor_id=monitor2.id, agendamento_id=ag2_atr.id),
        ])
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


def test_client_sees_only_own_data(client, app):
    with app.app_context():
        cliente1 = Cliente.query.filter_by(email='c1@test').first()
    with client:
        login_client_session(client, cliente1.id)
        resp = client.get('/distribuicao-manual')
        assert resp.status_code == 200

        today = datetime.now().date()
        c1_dates = [
            (today + timedelta(days=1)).strftime('%d/%m/%Y'),
            (today + timedelta(days=2)).strftime('%d/%m/%Y'),
        ]
        c2_dates = [
            (today + timedelta(days=3)).strftime('%d/%m/%Y'),
            (today + timedelta(days=4)).strftime('%d/%m/%Y'),
        ]

        assert b'Monitor1' in resp.data
        assert b'Monitor2' not in resp.data
        assert b'MonitorGlobal' in resp.data

        for d in c1_dates:
            assert d.encode() in resp.data
        for d in c2_dates:
            assert d.encode() not in resp.data


def test_client_can_assign_global_monitor(client, app):
    with app.app_context():
        cliente1 = Cliente.query.filter_by(email='c1@test').first()
        global_monitor = Monitor.query.filter_by(cliente_id=None).first()
        agendamento_sem_monitor = None
        agendamentos_cliente = AgendamentoVisita.query.filter_by(
            cliente_id=cliente1.id
        ).all()
        for agendamento in agendamentos_cliente:
            if not MonitorAgendamento.query.filter_by(
                agendamento_id=agendamento.id
            ).first():
                agendamento_sem_monitor = agendamento
                break
        assert agendamento_sem_monitor is not None

    with client:
        login_client_session(client, cliente1.id)
        resp = client.post(
            '/atribuir-monitor',
            data={
                'agendamento_id': agendamento_sem_monitor.id,
                'monitor_id': global_monitor.id,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

    with app.app_context():
        assert (
            MonitorAgendamento.query.filter_by(
                monitor_id=global_monitor.id,
                agendamento_id=agendamento_sem_monitor.id,
            ).count()
            == 1
        )

