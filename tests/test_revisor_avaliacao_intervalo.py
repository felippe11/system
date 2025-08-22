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

    Assignment,
    Cliente,
    Evento,
    EventoBarema,
    Review,
    Submission,
    Usuario,
)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome="C", email="c@test", senha=generate_password_hash("123", method="pbkdf2:sha256")
        )
        db.session.add(cliente)
        db.session.flush()

        evento = Evento(nome="E", cliente_id=cliente.id)
        reviewer = Usuario(
            nome="Rev",
            cpf="1",
            email="rev@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
            formacao="X",
            tipo="revisor",
        )
        submission = Submission(
            title="T",
            code_hash=generate_password_hash("code", method="pbkdf2:sha256"),
            evento_id=evento.id,
        )
        db.session.add_all([evento, reviewer, submission])
        db.session.flush()
        db.session.add(Assignment(submission_id=submission.id, reviewer_id=reviewer.id))
        db.session.add(
            EventoBarema(
                evento_id=evento.id,
                requisitos={"Qualidade": {"min": 1, "max": 5}},
            )
        )
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        "/login", data={"email": "rev@test", "senha": "123"}, follow_redirects=True
    )


def test_avaliar_accepts_score_within_range(client, app):
    with app.app_context():
        submission_id = Submission.query.first().id
    login(client)
    resp = client.post(
        f"/revisor/avaliar/{submission_id}",
        data={"Qualidade": "3"},
        follow_redirects=True,
    )
    assert "Avaliação registrada".encode() in resp.data
    with app.app_context():
        review = Review.query.first()
        assert review is not None
        assert review.scores == {"Qualidade": 3}


def test_avaliar_rejects_score_out_of_range(client, app):
    with app.app_context():
        submission_id = Submission.query.first().id
    login(client)
    resp = client.post(
        f"/revisor/avaliar/{submission_id}",
        data={"Qualidade": "6"},
        follow_redirects=True,
    )
    assert "deve estar entre 1 e 5".encode() in resp.data
    with app.app_context():
        review = Review.query.first()
        assert review is None


def test_avaliacao_template_shows_interval(client, app):
    with app.app_context():
        submission_id = Submission.query.first().id
    login(client)
    resp = client.get(f"/revisor/avaliar/{submission_id}")
    assert b"(1-5)" in resp.data
    assert b'min="1"' in resp.data
    assert b'max="5"' in resp.data

