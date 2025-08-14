import os
from datetime import date, time

import pytest
from werkzeug.security import generate_password_hash
from flask import template_rendered

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import Cliente, Evento, HorarioVisitacao, AgendamentoVisita


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
            nome='Cli',
            email='cli@test',
            senha=generate_password_hash('123'),
        )
        db.session.add(cliente)
        db.session.flush()

        evento1 = Evento(
            cliente_id=cliente.id,
            nome='Evento1',
            habilitar_lotes=False,
            inscricao_gratuita=True,
        )
        evento2 = Evento(
            cliente_id=cliente.id,
            nome='Evento2',
            habilitar_lotes=False,
            inscricao_gratuita=True,
        )
        db.session.add_all([evento1, evento2])
        db.session.flush()

        horario = HorarioVisitacao(
            evento_id=evento1.id,
            data=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
        )
        db.session.add(horario)
        db.session.flush()

        ag1 = AgendamentoVisita(
            horario_id=horario.id,
            professor_id=None,
            escola_nome='Esc1',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=10,
            status='confirmado',
        )
        ag2 = AgendamentoVisita(
            horario_id=horario.id,
            professor_id=None,
            escola_nome='Esc2',
            turma='T2',
            nivel_ensino='Fundamental',
            quantidade_alunos=15,
            status='realizado',
        )
        ag3 = AgendamentoVisita(
            horario_id=horario.id,
            professor_id=None,
            escola_nome='Esc3',
            turma='T3',
            nivel_ensino='Fundamental',
            quantidade_alunos=5,
            status='cancelado',
        )
        db.session.add_all([ag1, ag2, ag3])
        db.session.commit()

    yield app

    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha})


def test_relatorio_geral_agendamentos(app, client):
    login(client, 'cli@test', '123')
    captured = []

    def capture(sender, template, context, **extra):
        captured.append(context)

    with template_rendered.connected_to(capture, app):
        resp = client.get('/relatorio_geral_agendamentos')
    assert resp.status_code == 200
    assert captured

    context = captured[0]
    estatisticas = context['estatisticas']

    with app.app_context():
        evento1 = Evento.query.filter_by(nome='Evento1').first()
        evento2 = Evento.query.filter_by(nome='Evento2').first()

    assert estatisticas[evento1.id]['confirmados'] == 1
    assert estatisticas[evento1.id]['realizados'] == 1
    assert estatisticas[evento1.id]['cancelados'] == 1
    assert estatisticas[evento1.id]['visitantes'] == 25
    assert estatisticas[evento1.id]['total'] == 3

    assert estatisticas[evento2.id]['confirmados'] == 0
    assert estatisticas[evento2.id]['realizados'] == 0
    assert estatisticas[evento2.id]['cancelados'] == 0
    assert estatisticas[evento2.id]['visitantes'] == 0
    assert estatisticas[evento2.id]['total'] == 0
