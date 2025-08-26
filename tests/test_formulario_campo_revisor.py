import os
import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "y")
os.environ.setdefault("DB_PASS", "test")

from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import Formulario, CampoFormulario
from models.user import Cliente
from models.review import RevisorProcess


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
        campo_email = CampoFormulario(
            formulario_id=form.id,
            nome="email",
            tipo="text",
            obrigatorio=True,
        )
        campo_nome = CampoFormulario(
            formulario_id=form.id,
            nome="nome",
            tipo="text",
            obrigatorio=True,
        )
        db.session.add_all([campo_email, campo_nome])
        db.session.commit()
        proc = RevisorProcess(cliente_id=cliente.id, formulario_id=form.id, num_etapas=1)
        db.session.add(proc)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post("/login", data={"email": email, "senha": senha}, follow_redirects=True)


def test_cannot_rename_revisor_fields(client, app):
    with app.app_context():
        campo = CampoFormulario.query.filter_by(nome="email").first()
        campo_id = campo.id
    login(client, "cli@test", "123")
    resp = client.post(
        f"/campos/{campo_id}/editar",
        data={
            "nome": "novo",
            "tipo": "text",
            "obrigatorio": "on",
            "opcoes": "",
            "tamanho_max": "",
            "regex_validacao": "",
        },
    )
    assert resp.status_code == 200
    with app.app_context():
        campo = CampoFormulario.query.get(campo_id)
        assert campo.nome == "email"


def test_cannot_unset_required_revisor_fields(client, app):
    with app.app_context():
        campo = CampoFormulario.query.filter_by(nome="nome").first()
        campo_id = campo.id
    login(client, "cli@test", "123")
    resp = client.post(
        f"/campos/{campo_id}/editar",
        data={
            "nome": "nome",
            "tipo": "text",
            "opcoes": "",
            "tamanho_max": "",
            "regex_validacao": "",
        },
    )
    assert resp.status_code == 200
    with app.app_context():
        campo = CampoFormulario.query.get(campo_id)
        assert campo.obrigatorio is True
