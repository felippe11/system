import os

import pytest
from werkzeug.security import generate_password_hash

os.environ["SECRET_KEY"] = "test"
os.environ["GOOGLE_CLIENT_ID"] = "dummy"
os.environ["GOOGLE_CLIENT_SECRET"] = "dummy"

from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models.user import Usuario
from models.review import Submission, Assignment


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        db.create_all()
        reviewer = Usuario(
            nome="Rev", cpf="1", email="rev@test", senha=generate_password_hash("123", method="pbkdf2:sha256"),
            formacao="X", tipo="revisor"
        )
        submission = Submission(
            title="T",
            code_hash=generate_password_hash("code", method="pbkdf2:sha256"),
        )
        db.session.add_all([reviewer, submission])
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        "/login", data={"email": "rev@test", "senha": "123"}, follow_redirects=True
    )


def test_unassigned_reviewer_blocked(client, app):
    login(client)
    with app.app_context():
        submission_id = Submission.query.first().id
    resp = client.get(f"/revisor/avaliar/{submission_id}", follow_redirects=True)
    assert b"Acesso negado" in resp.data


def test_assigned_reviewer_can_access(client, app):
    with app.app_context():
        reviewer = Usuario.query.filter_by(email="rev@test").first()
        submission = Submission.query.first()
        db.session.add(Assignment(submission_id=submission.id, reviewer_id=reviewer.id))
        db.session.commit()
        submission_id = submission.id
    login(client)
    resp = client.get(f"/revisor/avaliar/{submission_id}")
    assert resp.status_code == 200
    assert b"Avaliar Trabalho" in resp.data
