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
            nome="Email",
            tipo="text",
            obrigatorio=True,
            protegido=True,
        )
        campo_nome = CampoFormulario(
            formulario_id=form.id,
            nome="Nome",
            tipo="text",
            obrigatorio=True,
            protegido=True,
        )
        db.session.add_all([campo_email, campo_nome])
        db.session.commit()
        proc = RevisorProcess(
            cliente_id=cliente.id,
            formulario_id=form.id,
            num_etapas=1,
            nome="Proc",
            status="ativo",
        )
        db.session.add(proc)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post("/login", data={"email": email, "senha": senha}, follow_redirects=True)


def test_can_rename_protected_fields(client, app):
    with app.app_context():
        campo_email = CampoFormulario.query.filter_by(nome="Email").first()
        email_id = campo_email.id
        campo_nome = CampoFormulario.query.filter_by(nome="Nome").first()
        nome_id = campo_nome.id
    login(client, "cli@test", "123")
    resp_email = client.post(
        f"/campos/{email_id}/editar",
        data={
            "nome": "novo_email",
            "tipo": "text",
            "obrigatorio": "on",
        },
        follow_redirects=True,
    )
    resp_nome = client.post(
        f"/campos/{nome_id}/editar",
        data={
            "nome": "novo_nome",
            "tipo": "text",
            "obrigatorio": "on",
        },
        follow_redirects=True,
    )
    assert resp_email.status_code == 200
    assert resp_nome.status_code == 200
    with app.app_context():
        campo_email = CampoFormulario.query.get(email_id)
        campo_nome = CampoFormulario.query.get(nome_id)
        assert campo_email.nome == "novo_email"
        assert campo_nome.nome == "novo_nome"


def test_cannot_modify_other_attributes(client, app):
    with app.app_context():
        campo = CampoFormulario.query.filter_by(nome="Email").first()
        campo_id = campo.id
    login(client, "cli@test", "123")
    resp = client.post(
        f"/campos/{campo_id}/editar",
        data={
            "nome": "email",
            "tipo": "number",
            "opcoes": "",
            "tamanho_max": "",
            "regex_validacao": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        campo = CampoFormulario.query.get(campo_id)
        assert campo.tipo == "text"
        assert campo.obrigatorio is True
