import pytest
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError

from config import Config
from app import create_app
from extensions import db
from models import Evento
from models.user import Usuario, Cliente

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
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome="Cli", email="cli@test", senha=generate_password_hash("123", method="pbkdf2:sha256")
        )
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome="EV")
        db.session.add(evento)
        usuario = Usuario(
            id=cliente.id,
            nome="CliUser",
            cpf="1",
            email="cli@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
            formacao="x",
            tipo="cliente",
        )
        db.session.add(usuario)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post(
        "/login", data={"email": email, "senha": senha}, follow_redirects=True
    )


def test_dashboard_cliente_db_error(client, app, monkeypatch):
    login(client, "cli@test", "123")

    def fail(*args, **kwargs):  # pragma: no cover - testing error path
        raise SQLAlchemyError("boom")

    with app.app_context():
        monkeypatch.setattr(Evento.query, "filter_by", fail)

    resp = client.get("/dashboard_cliente")
    assert resp.status_code == 200
    assert b"dashboard" in resp.data.lower()
