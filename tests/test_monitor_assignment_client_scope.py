import os
from datetime import date, time

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
        cliente1 = Cliente(nome='Cliente1', email='c1@test', senha='x')
        cliente2 = Cliente(nome='Cliente2', email='c2@test', senha='x')
        db.session.add_all([cliente1, cliente2])
        db.session.commit()

        monitor1 = Monitor(
            nome_completo='Monitor1',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda',
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
            dias_disponibilidade='segunda',
            turnos_disponibilidade='manha',
            email='m2@test',
            telefone_whatsapp='2',
            codigo_acesso='BBB222',
            cliente_id=cliente2.id,
        )
        db.session.add_all([monitor1, monitor2])

        evento = Evento(
            cliente_id=cliente1.id,
            nome='Evento1',
            habilitar_lotes=False,
            inscricao_gratuita=True,
        )
        db.session.add(evento)
        db.session.commit()

        horario = HorarioVisitacao(
            evento_id=evento.id,
            data=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
        )
        db.session.add(horario)
        db.session.commit()

        agendamento = AgendamentoVisita(
            horario_id=horario.id,
            cliente_id=cliente1.id,
            escola_nome='Escola',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=10,
            salas_selecionadas='1',
            status='pendente',
        )
        db.session.add(agendamento)
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


def test_client_cannot_assign_other_clients_monitor(app, client):
    with app.app_context():
        agendamento = AgendamentoVisita.query.first()
        monitor = Monitor.query.filter_by(email='m2@test').first()
        cliente1 = Cliente.query.filter_by(email='c1@test').first()

    with client:
        login_client_session(client, cliente1.id)
        resp = client.post(
            '/atribuir-monitor',
            data={'agendamento_id': agendamento.id, 'monitor_id': monitor.id},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is False
        assert 'Acesso negado' in data['message']

    with app.app_context():
        assert MonitorAgendamento.query.count() == 0
