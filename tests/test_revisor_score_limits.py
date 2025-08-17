import os

import pytest
from werkzeug.security import generate_password_hash

os.environ["SECRET_KEY"] = "test"
os.environ["GOOGLE_CLIENT_ID"] = "dummy"
os.environ["GOOGLE_CLIENT_SECRET"] = "dummy"

from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db

    Usuario,
    Cliente,
    Evento,
    Submission,
    Assignment,
    RevisorProcess,
    ProcessoBarema,
    ProcessoBaremaRequisito,
    EventoBarema,
    Review,
)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome="Cli",
            email="cli@test",
            senha=generate_password_hash("123"),
        )
        db.session.add(cliente)
        db.session.flush()
        reviewer = Usuario(
            nome="Rev",
            cpf="1",
            email="rev@test",
            senha=generate_password_hash("123"),
            formacao="X",
            tipo="revisor",
        )
        process = RevisorProcess(cliente_id=cliente.id, num_etapas=1)
        db.session.add_all([reviewer, process])
        db.session.flush()
        barema_proc = ProcessoBarema(process_id=process.id)
        db.session.add(barema_proc)
        db.session.flush()
        requisito = ProcessoBaremaRequisito(
            barema_id=barema_proc.id,
            nome="Qualidade",
            pontuacao_min=1,
            pontuacao_max=5,
        )
        evento = Evento(
            cliente_id=cliente.id,
            nome="Evento",
            inscricao_gratuita=True,
        )
        db.session.add_all([requisito, evento])
        db.session.flush()
        process.eventos.append(evento)
        evento_barema = EventoBarema(evento_id=evento.id, requisitos={"Qualidade": 5})
        submission = Submission(
            title="T",
            code_hash=generate_password_hash("code"),
            evento_id=evento.id,
        )
        assignment = Assignment(submission=submission, reviewer=reviewer)
        db.session.add_all([evento_barema, submission, assignment])
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        "/login",
        data={"email": "rev@test", "senha": "123"},
        follow_redirects=True,
    )


def get_submission_id(app):
    with app.app_context():
        return Submission.query.first().id


def test_score_below_min_rejected(client, app):
    login(client)
    sub_id = get_submission_id(app)
    client.post(
        f"/revisor/avaliar/{sub_id}",
        data={"Qualidade": "0"},
        follow_redirects=True,
    )
    with app.app_context():
        assert Review.query.count() == 0


def test_score_above_max_rejected(client, app):
    login(client)
    sub_id = get_submission_id(app)
    client.post(
        f"/revisor/avaliar/{sub_id}",
        data={"Qualidade": "6"},
        follow_redirects=True,
    )
    with app.app_context():
        assert Review.query.count() == 0
