import os
from datetime import date, time
import pytest

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("DB_PASS", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")

from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db, login_manager
from models import (
    Cliente,
    Monitor,
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

        monitor2 = Monitor(
            nome_completo='Monitor2',
            curso='C',
            carga_horaria_disponibilidade=10,
            dias_disponibilidade='segunda',
            turnos_disponibilidade='manha',
            email='m2@test',
            telefone_whatsapp='1',
            codigo_acesso='ABC123',
            cliente_id=cliente2.id,
        )
        db.session.add(monitor2)
        db.session.commit()

        evento2 = Evento(cliente_id=cliente2.id, nome='Evento2')
        db.session.add(evento2)
        db.session.commit()

        horario = HorarioVisitacao(
            evento_id=evento2.id,
            data=date.today(),
            horario_inicio=time(8, 0),
            horario_fim=time(9, 0),
            capacidade_total=10,
            vagas_disponiveis=10,
            fechado=False,
        )
        db.session.add(horario)
        db.session.commit()

        agendamento = AgendamentoVisita(
            horario_id=horario.id,
            cliente_id=cliente2.id,
            escola_nome='Escola',
            turma='1A',
            nivel_ensino='fundamental',
            quantidade_alunos=10,
        )
        db.session.add(agendamento)
        db.session.commit()

        atribuicao = MonitorAgendamento(
            monitor_id=monitor2.id,
            agendamento_id=agendamento.id,
        )
        db.session.add(atribuicao)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login_cliente_session(client, cliente_id):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_id)
        sess['_fresh'] = True
        sess['_id'] = 'test-session'
        sess['user_type'] = 'cliente'


def test_client_cannot_remove_other_assignment(client, app):
    with app.app_context():
        cliente1 = Cliente.query.filter_by(email='c1@test').first()
        atrib = MonitorAgendamento.query.first()
    with client:
        login_cliente_session(client, cliente1.id)
        resp = client.post(
            '/remover-atribuicao', data={'agendamento_id': atrib.agendamento_id}
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is False
    with app.app_context():
        assert MonitorAgendamento.query.count() == 1
