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
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.build_engine_options(
        app.config["SQLALCHEMY_DATABASE_URI"]
    )
    with app.app_context():
        db.create_all()

        cliente = Cliente(nome="Cliente", email="c@test", senha="x")
        db.session.add(cliente)
        db.session.commit()

        monitor1 = Monitor(
            nome_completo="Monitor1",
            curso="C",
            carga_horaria_disponibilidade=10,
            dias_disponibilidade="segunda",
            turnos_disponibilidade="manha",
            email="m1@test",
            telefone_whatsapp="1",
            codigo_acesso="AAA111",
            cliente_id=cliente.id,
        )
        monitor2 = Monitor(
            nome_completo="Monitor2",
            curso="C",
            carga_horaria_disponibilidade=10,
            dias_disponibilidade="segunda",
            turnos_disponibilidade="manha",
            email="m2@test",
            telefone_whatsapp="2",
            codigo_acesso="BBB222",
            cliente_id=cliente.id,
        )
        db.session.add_all([monitor1, monitor2])
        db.session.commit()

        evento = Evento(cliente_id=cliente.id, nome="Evento")
        db.session.add(evento)
        db.session.commit()

        horario = HorarioVisitacao(
            evento_id=evento.id,
            data=date.today(),
            horario_inicio=time(8, 0),
            horario_fim=time(9, 0),
            capacidade_total=10,
            vagas_disponiveis=10,
            fechado=False,
        )
        db.session.add(horario)
        db.session.commit()

        ag1 = AgendamentoVisita(
            horario_id=horario.id,
            cliente_id=cliente.id,
            escola_nome="Escola1",
            turma="1A",
            nivel_ensino="fundamental",
            quantidade_alunos=10,
        )
        ag2 = AgendamentoVisita(
            horario_id=horario.id,
            cliente_id=cliente.id,
            escola_nome="Escola2",
            turma="1B",
            nivel_ensino="fundamental",
            quantidade_alunos=10,
        )
        db.session.add_all([ag1, ag2])
        db.session.commit()

        a1 = MonitorAgendamento(monitor_id=monitor1.id, agendamento_id=ag1.id)
        a2 = MonitorAgendamento(monitor_id=monitor2.id, agendamento_id=ag2.id)
        db.session.add_all([a1, a2])
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login_cliente_session(client, cliente_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(cliente_id)
        sess["_fresh"] = True
        sess["_id"] = "test-session"
        sess["user_type"] = "cliente"


def test_reset_agendamentos_monitor(client, app):
    with app.app_context():
        cliente = Cliente.query.filter_by(email="c@test").first()
        monitor = Monitor.query.filter_by(codigo_acesso="AAA111").first()
        atrib = MonitorAgendamento.query.filter_by(monitor_id=monitor.id).first()
        assert atrib.status == "ativo"
    with client:
        login_cliente_session(client, cliente.id)
        resp = client.post("/reset-agendamentos", json={"monitor_id": monitor.id})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["removidos"] == 1
    with app.app_context():
        atrib = MonitorAgendamento.query.filter_by(monitor_id=monitor.id).first()
        assert atrib.status == "inativo"


def test_reset_agendamentos_all(client, app):
    with app.app_context():
        cliente = Cliente.query.filter_by(email="c@test").first()
    with client:
        login_cliente_session(client, cliente.id)
        resp = client.post("/reset-agendamentos")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["removidos"] == 2
    with app.app_context():
        assert all(ma.status == "inativo" for ma in MonitorAgendamento.query.all())
