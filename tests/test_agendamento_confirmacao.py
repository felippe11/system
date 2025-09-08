import os
from datetime import date, time

import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('DB_PASS', 'test')
os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('DB_PASS', 'test')

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import (
    Cliente,
    Usuario,
    Evento,
    HorarioVisitacao,
    SalaVisitacao,
    AgendamentoVisita,
    NotificacaoAgendamento,
)
from routes import agendamento_routes


@pytest.fixture
def app():
    os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
    os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
    os.environ.setdefault('SECRET_KEY', 'test')

    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.drop_all()
        db.create_all()
        cliente = Cliente(
            nome='Cli', email='cli@test', senha=generate_password_hash('123', method="pbkdf2:sha256")
        )
        db.session.add(cliente)
        db.session.flush()
        evento = Evento(
            cliente_id=cliente.id,
            nome='Evento',
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

        professor = Usuario(
            id=100,
            nome='Prof',
            cpf='111',
            email='prof@test',
            senha=generate_password_hash('p123', method="pbkdf2:sha256"),
            formacao='F',
            tipo='professor',
        )
        outro_prof = Usuario(
            id=101,
            nome='Prof2',
            cpf='222',
            email='prof2@test',
            senha=generate_password_hash('p123', method="pbkdf2:sha256"),
            formacao='F',
            tipo='professor',
        )
        participante = Usuario(
            id=102,
            nome='Part',
            cpf='333',
            email='part@test',
            senha=generate_password_hash('p123', method="pbkdf2:sha256"),
            formacao='F',
            tipo='participante',
        )
        db.session.add_all([professor, outro_prof, participante])
        db.session.commit()

        agendamento = AgendamentoVisita(
            horario_id=horario.id,
            professor_id=professor.id,
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


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha})


def get_agendamento(app):
    with app.app_context():
        return AgendamentoVisita.query.first()


def test_professor_pode_confirmar_agendamento(client, app, monkeypatch):
    monkeypatch.setattr(
        agendamento_routes.NotificacaoAgendamentoService,
        'enviar_email_confirmacao',
        lambda ag: None,
    )
    login(client, 'prof@test', 'p123')
    agendamento = get_agendamento(app)
    resp = client.put(
        f'/atualizar_status/{agendamento.id}', json={'status': 'confirmado'}
    )
    assert resp.status_code == 200
    with app.app_context():
        assert AgendamentoVisita.query.get(agendamento.id).status == 'confirmado'


def test_cliente_pode_confirmar_agendamento(client, app, monkeypatch):
    monkeypatch.setattr(
        agendamento_routes.NotificacaoAgendamentoService,
        'enviar_email_confirmacao',
        lambda ag: None,
    )
    login(client, 'cli@test', '123')
    agendamento = get_agendamento(app)
    resp = client.put(
        f'/atualizar_status/{agendamento.id}', json={'status': 'confirmado'}
    )
    assert resp.status_code == 200
    with app.app_context():
        assert AgendamentoVisita.query.get(agendamento.id).status == 'confirmado'


def test_outro_professor_nao_pode_confirmar(client, app):
    login(client, 'prof2@test', 'p123')
    agendamento = get_agendamento(app)
    resp = client.put(
        f'/atualizar_status/{agendamento.id}', json={'status': 'confirmado'}
    )
    assert resp.status_code == 403


def test_email_enviado_quando_confirmado(client, app, monkeypatch):
    login(client, 'prof@test', 'p123')
    agendamento = get_agendamento(app)

    enviado = {'chamado': False}

    def fake_enviar_email(ag):
        enviado['chamado'] = True
        assert ag.id == agendamento.id

    monkeypatch.setattr(
        agendamento_routes.NotificacaoAgendamentoService,
        'enviar_email_confirmacao',
        fake_enviar_email,
    )

    resp = client.put(
        f'/atualizar_status/{agendamento.id}', json={'status': 'confirmado'}
    )
    assert resp.status_code == 200
    assert enviado['chamado']


def test_email_nao_enviado_para_outros_status(client, app, monkeypatch):
    login(client, 'prof@test', 'p123')
    agendamento = get_agendamento(app)

    chamado = {'count': 0}

    def fake_enviar_email(_):
        chamado['count'] += 1

    monkeypatch.setattr(
        agendamento_routes.NotificacaoAgendamentoService,
        'enviar_email_confirmacao',
        fake_enviar_email,
    )

    resp = client.put(
        f'/atualizar_status/{agendamento.id}', json={'status': 'cancelado'}
    )
    assert resp.status_code == 200
    assert chamado['count'] == 0


def test_redirecionamento_professor(client, app, monkeypatch):
    monkeypatch.setattr(
        agendamento_routes.NotificacaoAgendamentoService,
        'enviar_email_confirmacao',
        lambda ag: None,
    )
    login(client, 'prof@test', 'p123')
    with app.app_context():
        agendamento = AgendamentoVisita.query.first()
        agendamento.quantidade_alunos = 0
        db.session.commit()
        agendamento_id = agendamento.id
    resp = client.post(
        f'/atualizar_status/{agendamento_id}',
        data={'status': 'confirmado'},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert '/professor/meus_agendamentos' in resp.headers['Location']


def test_redirecionamento_participante(client, app, monkeypatch):
    monkeypatch.setattr(
        agendamento_routes.NotificacaoAgendamentoService,
        'enviar_email_confirmacao',
        lambda ag: None,
    )
    login(client, 'part@test', 'p123')
    with app.app_context():
        participante = Usuario.query.filter_by(email='part@test').first()
        agendamento = AgendamentoVisita.query.first()
        agendamento.professor_id = participante.id
        db.session.commit()
        agendamento_id = agendamento.id
    resp = client.post(
        f'/atualizar_status/{agendamento_id}',
        data={'status': 'confirmado'},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert '/participante/meus_agendamentos' in resp.headers['Location']


def test_redirecionamento_cliente(client, app, monkeypatch):
    monkeypatch.setattr(
        agendamento_routes.NotificacaoAgendamentoService,
        'enviar_email_confirmacao',
        lambda ag: None,
    )
    login(client, 'cli@test', '123')
    agendamento = get_agendamento(app)
    resp = client.post(
        f'/atualizar_status/{agendamento.id}',
        data={'status': 'confirmado'},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert '/cliente/meus_agendamentos' in resp.headers['Location']


def test_nao_lidas_count_endpoint(client, app):
    login(client, 'prof@test', 'p123')
    with app.app_context():
        agendamento = AgendamentoVisita.query.first()
        professor = Usuario.query.filter_by(email='prof@test').first()
        notificacoes = [
            NotificacaoAgendamento(
                agendamento_id=agendamento.id,
                remetente_id=professor.id,
                destinatario_id=professor.id,
                tipo='mensagem',
                titulo='t1',
                mensagem='m1',
            ),
            NotificacaoAgendamento(
                agendamento_id=agendamento.id,
                remetente_id=professor.id,
                destinatario_id=professor.id,
                tipo='mensagem',
                titulo='t2',
                mensagem='m2',
            ),
        ]
        db.session.add_all(notificacoes)
        db.session.commit()

    resp = client.get('/api/notificacoes/nao-lidas/count')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['count'] == 2
