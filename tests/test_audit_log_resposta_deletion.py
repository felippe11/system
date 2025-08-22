import os

import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test")

from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db

    Cliente,
    Usuario,
    Formulario,
    RespostaFormulario,
    AuditLog,
)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"

    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome="Cli",
            email="cli@example.com",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
        )
        db.session.add(cliente)
        db.session.commit()

        participante = Usuario(
            nome="User",
            cpf="1",
            email="user@example.com",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
            formacao="x",
            tipo="participante",
            cliente_id=cliente.id,
        )
        db.session.add(participante)
        db.session.commit()

        formulario = Formulario(nome="F1", cliente_id=cliente.id)
        db.session.add(formulario)
        db.session.commit()

        resposta = RespostaFormulario(
            formulario_id=formulario.id,
            usuario_id=participante.id,
        )
        db.session.add(resposta)
        db.session.commit()

        log = AuditLog(
            user_id=participante.id,
            submission_id=resposta.id,
            event_type="test",
        )
        db.session.add(log)
        db.session.commit()

        app.resposta_id = resposta.id
        app.cliente_email = cliente.email

    yield app

    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post(
        "/login", data={"email": email, "senha": senha}, follow_redirects=True
    )


def test_delete_response_cascades_audit_logs(app, client):
    login(client, app.cliente_email, "123")
    resp = client.post(
        f"/respostas/{app.resposta_id}/deletar", follow_redirects=True
    )
    assert resp.status_code in (200, 302)

    with app.app_context():
        assert RespostaFormulario.query.get(app.resposta_id) is None
        assert AuditLog.query.filter_by(submission_id=app.resposta_id).count() == 0
        log = AuditLog.query.filter_by(event_type="delete_resposta").first()
        assert log is not None and log.submission_id is None
