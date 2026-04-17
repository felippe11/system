import os
from datetime import datetime, time, timedelta

import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-secret")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from config import Config
from app import create_app
from extensions import db
from models import (
    AgendamentoVisita,
    Checkin,
    Evento,
    EventoInscricaoTipo,
    HorarioVisitacao,
    Inscricao,
    Oficina,
)
from models.user import Cliente, Usuario

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"

    agora = datetime.utcnow()
    hoje = agora.date()

    with app.app_context():
        db.create_all()

        cliente = Cliente(
            nome="Cliente Principal",
            email="cliente@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
        )
        outro_cliente = Cliente(
            nome="Outro Cliente",
            email="outro@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
        )
        db.session.add_all([cliente, outro_cliente])
        db.session.flush()

        usuario_cliente = Usuario(
            id=cliente.id,
            nome="Cliente Principal",
            cpf="10000000001",
            email="cliente@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
            formacao="Gestao",
            tipo="cliente",
        )
        participantes = [
            Usuario(
                nome="Participante 1",
                cpf="10000000002",
                email="p1@test",
                senha=generate_password_hash("123", method="pbkdf2:sha256"),
                formacao="Aluno",
                tipo="participante",
            ),
            Usuario(
                nome="Participante 2",
                cpf="10000000003",
                email="p2@test",
                senha=generate_password_hash("123", method="pbkdf2:sha256"),
                formacao="Aluno",
                tipo="participante",
            ),
            Usuario(
                nome="Participante 3",
                cpf="10000000004",
                email="p3@test",
                senha=generate_password_hash("123", method="pbkdf2:sha256"),
                formacao="Aluno",
                tipo="participante",
            ),
            Usuario(
                nome="Participante Externo",
                cpf="10000000005",
                email="externo@test",
                senha=generate_password_hash("123", method="pbkdf2:sha256"),
                formacao="Aluno",
                tipo="participante",
            ),
        ]
        db.session.add(usuario_cliente)
        db.session.add_all(participantes)
        db.session.flush()

        evento_ativo = Evento(
            cliente_id=cliente.id,
            nome="Evento Ativo",
            data_inicio=agora - timedelta(days=1),
            data_fim=agora + timedelta(days=1),
            status="ativo",
        )
        evento_futuro = Evento(
            cliente_id=cliente.id,
            nome="Evento Futuro",
            data_inicio=agora + timedelta(days=5),
            data_fim=agora + timedelta(days=6),
            status="ativo",
        )
        evento_encerrado = Evento(
            cliente_id=cliente.id,
            nome="Evento Encerrado",
            data_inicio=agora - timedelta(days=10),
            data_fim=agora - timedelta(days=5),
            status="encerrado",
        )
        db.session.add_all([evento_ativo, evento_futuro, evento_encerrado])
        db.session.flush()

        tipo_inscricao = EventoInscricaoTipo(
            evento_id=evento_ativo.id,
            nome="Ingresso Geral",
            preco=150.0,
        )
        db.session.add(tipo_inscricao)
        db.session.flush()

        oficina_limitada = Oficina(
            titulo="Oficina Limitada",
            descricao="Atividade com vagas limitadas",
            ministrante_id=None,
            vagas=10,
            carga_horaria="4h",
            estado="CE",
            cidade="Fortaleza",
            cliente_id=cliente.id,
            evento_id=evento_ativo.id,
            tipo_inscricao="com_inscricao_com_limite",
        )
        oficina_ilimitada = Oficina(
            titulo="Oficina Ilimitada",
            descricao="Atividade sem limite",
            ministrante_id=None,
            vagas=0,
            carga_horaria="4h",
            estado="CE",
            cidade="Fortaleza",
            cliente_id=cliente.id,
            evento_id=evento_ativo.id,
            tipo_inscricao="com_inscricao_sem_limite",
        )
        oficina_global = Oficina(
            titulo="Oficina Global",
            descricao="Atividade sem vínculo com cliente",
            ministrante_id=None,
            vagas=5,
            carga_horaria="4h",
            estado="CE",
            cidade="Fortaleza",
            cliente_id=None,
            evento_id=evento_ativo.id,
            tipo_inscricao="com_inscricao_com_limite",
        )
        db.session.add_all([oficina_limitada, oficina_ilimitada, oficina_global])
        db.session.flush()

        db.session.add_all(
            [
                Inscricao(
                    usuario_id=participantes[0].id,
                    cliente_id=cliente.id,
                    oficina_id=oficina_limitada.id,
                    evento_id=evento_ativo.id,
                    status_pagamento="approved",
                    tipo_inscricao_id=tipo_inscricao.id,
                ),
                Inscricao(
                    usuario_id=participantes[1].id,
                    cliente_id=cliente.id,
                    oficina_id=oficina_limitada.id,
                    evento_id=evento_ativo.id,
                    status_pagamento="pending",
                    tipo_inscricao_id=tipo_inscricao.id,
                ),
                Inscricao(
                    usuario_id=participantes[2].id,
                    cliente_id=cliente.id,
                    oficina_id=oficina_ilimitada.id,
                    evento_id=evento_ativo.id,
                    status_pagamento="paid",
                    tipo_inscricao_id=tipo_inscricao.id,
                ),
                Inscricao(
                    usuario_id=participantes[3].id,
                    cliente_id=outro_cliente.id,
                    oficina_id=oficina_global.id,
                    evento_id=evento_ativo.id,
                    status_pagamento="approved",
                    tipo_inscricao_id=tipo_inscricao.id,
                ),
            ]
        )

        db.session.add(
            Checkin(
                usuario_id=participantes[0].id,
                oficina_id=oficina_limitada.id,
                evento_id=evento_ativo.id,
                cliente_id=cliente.id,
                palavra_chave="QR-OFICINA",
            )
        )

        horario_hoje = HorarioVisitacao(
            evento_id=evento_ativo.id,
            data=hoje,
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=40,
            vagas_disponiveis=30,
            fechado=False,
        )
        horario_futuro = HorarioVisitacao(
            evento_id=evento_futuro.id,
            data=hoje + timedelta(days=3),
            horario_inicio=time(14, 0),
            horario_fim=time(15, 0),
            capacidade_total=20,
            vagas_disponiveis=10,
            fechado=False,
        )
        db.session.add_all([horario_hoje, horario_futuro])
        db.session.flush()

        db.session.add_all(
            [
                AgendamentoVisita(
                    horario_id=horario_hoje.id,
                    professor_id=participantes[0].id,
                    cliente_id=cliente.id,
                    escola_nome="Escola A",
                    turma="Turma 1",
                    nivel_ensino="Fundamental",
                    quantidade_alunos=10,
                    status="confirmado",
                ),
                AgendamentoVisita(
                    horario_id=horario_hoje.id,
                    professor_id=participantes[1].id,
                    cliente_id=cliente.id,
                    escola_nome="Escola B",
                    turma="Turma 2",
                    nivel_ensino="Fundamental",
                    quantidade_alunos=7,
                    status="realizado",
                ),
                AgendamentoVisita(
                    horario_id=horario_hoje.id,
                    professor_id=participantes[2].id,
                    cliente_id=cliente.id,
                    escola_nome="Escola C",
                    turma="Turma 3",
                    nivel_ensino="Fundamental",
                    quantidade_alunos=3,
                    status="cancelado",
                ),
                AgendamentoVisita(
                    horario_id=horario_futuro.id,
                    professor_id=participantes[3].id,
                    cliente_id=cliente.id,
                    escola_nome="Escola D",
                    turma="Turma 4",
                    nivel_ensino="Fundamental",
                    quantidade_alunos=5,
                    status="pendente",
                ),
            ]
        )

        db.session.commit()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        "/login",
        data={"email": "cliente@test", "senha": "123"},
        follow_redirects=True,
    )


def test_dashboard_cliente_stats_context(client, monkeypatch):
    import routes.dashboard_cliente as dashboard_cliente_module

    captured = {}

    def fake_render(template_name, **context):
        captured["template"] = template_name
        captured["context"] = context
        return "dashboard-cliente"

    monkeypatch.setattr(dashboard_cliente_module, "render_template", fake_render)

    login(client)
    response = client.get("/dashboard_cliente")

    assert response.status_code == 200
    assert captured["template"] == "dashboard_cliente.html"

    context = captured["context"]
    oficinas_por_titulo = {oficina.titulo: oficina for oficina in context["oficinas"]}

    assert context["total_oficinas"] == 2
    assert set(oficinas_por_titulo) == {"Oficina Limitada", "Oficina Ilimitada"}
    assert context["total_inscricoes"] == 2
    assert context["total_vagas"] == 11
    assert context["percentual_adesao"] == pytest.approx(18.1818, rel=1e-3)
    assert context["checkins_por_oficina"][oficinas_por_titulo["Oficina Limitada"].id] == 1
    assert (
        context["inscricoes_por_oficina"].get(
            oficinas_por_titulo["Oficina Limitada"].id
        )
        == 1
    ), context["inscricoes_por_oficina"]
    assert (
        context["inscricoes_por_oficina"].get(
            oficinas_por_titulo["Oficina Ilimitada"].id
        )
        == 1
    ), context["inscricoes_por_oficina"]
    assert len(context["tipos"]) == 1
    assert context["tipos"][0].nome == "Ingresso Geral"
    assert context["tipos"][0].quantidade == 2
    assert context["valor_caixa"] == pytest.approx(300.0)


def test_dashboard_agendamentos_context(client, monkeypatch):
    import routes.dashboard_cliente as dashboard_cliente_module

    captured = {}

    def fake_render(template_name, **context):
        captured["template"] = template_name
        captured["context"] = context
        return "dashboard-agendamentos"

    monkeypatch.setattr(dashboard_cliente_module, "render_template", fake_render)

    login(client)
    response = client.get("/dashboard-agendamentos")

    assert response.status_code == 200
    assert captured["template"] == "agendamento/dashboard_agendamentos.html"

    context = captured["context"]

    assert context["total_eventos_com_agendamentos"] == 3
    assert len(context["eventos_cliente"]) == 3
    assert len(context["eventos_ativos"]) == 1
    assert len(context["eventos_futuros"]) == 1
    assert len(context["eventos_encerrados"]) == 1
    assert context["agendamentos_totais"] == 4
    assert context["agendamentos_confirmados"] == 1
    assert context["agendamentos_realizados"] == 1
    assert context["agendamentos_cancelados"] == 1
    assert context["total_visitantes"] == 17
    assert len(context["todos_agendamentos_hoje"]) == 1
    assert len(context["agendamentos_futuros"]) == 1
    assert context["ocupacao_media"] == pytest.approx(33.3333, rel=1e-3)
