import os
from datetime import date, time

import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
os.environ.setdefault('SECRET_KEY', 'test')

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import (
    Usuario,
    Cliente,
    Evento,
    HorarioVisitacao,
    AgendamentoVisita,
    AlunoVisitante,
)
from services import pdf_service


@pytest.fixture
def app(monkeypatch):
    def dummy_pdf(agendamento, horario, evento, salas, alunos, pdf_path):
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        with open(pdf_path, 'wb') as fh:
            fh.write(b'PDF')
        return pdf_path

    monkeypatch.setattr(
        pdf_service, 'gerar_pdf_comprovante_agendamento', dummy_pdf
    )

    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()

        cliente = Cliente(
            nome='Cliente',
            email='cli@test',
            senha=generate_password_hash('123'),
        )
        db.session.add(cliente)

        professor = Usuario(
            nome='Prof',
            cpf='1',
            email='prof@test',
            senha=generate_password_hash('123'),
            formacao='x',
            tipo='professor',
        )
        participante = Usuario(
            nome='Part',
            cpf='2',
            email='part@test',
            senha=generate_password_hash('123'),
            formacao='x',
            tipo='participante',
        )
        usuario = Usuario(
            nome='User',
            cpf='3',
            email='user@test',
            senha=generate_password_hash('123'),
            formacao='x',
            tipo='usuario',
        )
        db.session.add_all([professor, participante, usuario])
        db.session.commit()

        evento = Evento(cliente_id=cliente.id, nome='Evento')
        db.session.add(evento)
        db.session.commit()

        horario = HorarioVisitacao(
            evento_id=evento.id,
            data=date.today(),
            horario_inicio=time(10, 0),
            horario_fim=time(11, 0),
            capacidade_total=10,
            vagas_disponiveis=10,
        )
        db.session.add(horario)
        db.session.commit()

        agendamento = AgendamentoVisita(
            horario_id=horario.id,
            professor_id=professor.id,
            escola_nome='Escola',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=1,
            qr_code_token='token123',
        )
        db.session.add(agendamento)
        db.session.commit()

        aluno = AlunoVisitante(agendamento_id=agendamento.id, nome='Aluno')
        db.session.add(aluno)
        db.session.commit()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email):
    return client.post(
        '/login',
        data={'email': email, 'senha': '123'},
        follow_redirects=False,
    )


@pytest.mark.parametrize(
    'email',
    ['prof@test', 'part@test', 'cli@test', 'user@test'],
)
def test_imprimir_agendamento_access(app, client, email):
    from models import AgendamentoVisita
    from extensions import db

    login(client, email)
    with app.app_context():
        agendamento = AgendamentoVisita.query.first()
        agendamento.status = 'confirmado'
        db.session.commit()
        agendamento_id = agendamento.id
    resp = client.get(f'/professor/imprimir_agendamento/{agendamento_id}')
    assert resp.status_code == 200
    assert resp.data.startswith(b'PDF')


@pytest.mark.parametrize(
    'email',
    ['prof@test', 'part@test', 'cli@test', 'user@test'],
)
def test_qrcode_agendamento_access(app, client, email):
    from models import AgendamentoVisita
    from extensions import db

    login(client, email)
    with app.app_context():
        agendamento = AgendamentoVisita.query.first()
        agendamento.status = 'confirmado'
        db.session.commit()
        agendamento_id = agendamento.id
    resp = client.get(f'/professor/qrcode_agendamento/{agendamento_id}')
    assert resp.status_code == 200
    assert b'QR Code do Agendamento' in resp.data
