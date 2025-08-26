import os
import pytest
from werkzeug.security import generate_password_hash

os.environ["SECRET_KEY"] = "test-key"
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")
os.environ.setdefault("DB_PASS", "test")
from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import (
    Cliente,
    Formulario,
    CampoFormulario,
    Usuario,
    RevisorProcess,
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
            email="cli@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
        )
        db.session.add(cliente)
        db.session.commit()

        form = Formulario(nome="F1", cliente_id=cliente.id)
        db.session.add(form)
        db.session.commit()

        campo_nome = CampoFormulario(formulario_id=form.id, nome="nome", tipo="texto")
        campo_email = CampoFormulario(formulario_id=form.id, nome="email", tipo="texto")
        campo_idade = CampoFormulario(formulario_id=form.id, nome="idade", tipo="texto")
        db.session.add_all([campo_nome, campo_email, campo_idade])
        db.session.commit()

        usuario = Usuario(
            nome="User",
            cpf="00000000000000",
            email="user@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
            formacao="None",
        )
        db.session.add(usuario)
        db.session.commit()

        processo = RevisorProcess(
            cliente_id=cliente.id, formulario_id=form.id, num_etapas=1
        )
        db.session.add(processo)
        db.session.commit()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        "/login", data={"email": "cli@test", "senha": "123"}, follow_redirects=False
    )


def test_mandatory_fields_not_deleted(client, app):
    login(client)
    with app.app_context():
        campo_nome = CampoFormulario.query.filter_by(nome="nome").first()
        campo_email = CampoFormulario.query.filter_by(nome="email").first()
        campo_idade = CampoFormulario.query.filter_by(nome="idade").first()

    client.post(f"/campos/{campo_nome.id}/deletar")
    client.post(f"/campos/{campo_email.id}/deletar")
    client.post(f"/campos/{campo_idade.id}/deletar")

    with app.app_context():
        assert CampoFormulario.query.get(campo_nome.id) is not None
        assert CampoFormulario.query.get(campo_email.id) is not None
        assert CampoFormulario.query.get(campo_idade.id) is None

