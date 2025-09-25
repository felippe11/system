import os
import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")
os.environ.setdefault("DB_PASS", "test")

from config import Config

# Configure in-memory database for tests
Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models.user import Cliente
from models.event import Evento, RespostaFormulario
from models.event import Formulario, CampoFormulario
from models.review import Submission


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
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
        )
        db.session.add(cliente)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        "/login", data={"email": "cli@test", "senha": "123"}, follow_redirects=False
    )


def test_listar_trabalhos_with_and_without_form(client, app):
    login(client)
    resp = client.get("/trabalhos")
    assert resp.status_code == 200
    assert b"executar_formulario_trabalhos.py" in resp.data

    with app.app_context():
        cliente = Cliente.query.filter_by(email="cli@test").first()
        formulario = Formulario(
            nome="Formul\u00e1rio de Trabalhos", cliente_id=cliente.id
        )
        db.session.add(formulario)
        db.session.commit()

    resp = client.get("/trabalhos")
    assert resp.status_code == 200
    assert b"Meus Trabalhos" in resp.data


def test_novo_trabalho_with_and_without_form(client, app):
    login(client)
    resp = client.get("/trabalhos/novo")
    assert resp.status_code == 200
    assert b"executar_formulario_trabalhos.py" in resp.data

    with app.app_context():
        cliente = Cliente.query.filter_by(email="cli@test").first()
        formulario = Formulario(
            nome="Formul\u00e1rio de Trabalhos", cliente_id=cliente.id
        )
        campo = CampoFormulario(
            formulario_id=formulario.id, nome="Titulo", tipo="text"
        )
        evento = Evento(cliente_id=cliente.id, nome="E1")
        db.session.add_all([formulario, campo, evento])
        db.session.commit()

    resp = client.get("/trabalhos/novo")
    assert resp.status_code == 200
    assert b"Adicionar Novo Trabalho" in resp.data


def test_cliente_pode_criar_trabalho_sem_usuario_vinculado(client, app):
    login(client)
    with app.app_context():
        cliente = Cliente.query.filter_by(email="cli@test").first()
        formulario = Formulario(
            nome="Formulário de Trabalhos", cliente_id=cliente.id
        )
        campo = CampoFormulario(nome="Título", tipo="text")
        formulario.campos.append(campo)
        evento = Evento(cliente_id=cliente.id, nome="E1")
        db.session.add_all([formulario, evento])
        db.session.commit()

        campo_id = campo.id
        evento_id = evento.id

    resp = client.post(
        "/trabalhos/novo",
        data={
            "evento_id": str(evento_id),
            f"campo_{campo_id}": "Meu Trabalho",
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302

    with app.app_context():
        submission = Submission.query.one()
        assert submission.author_id is None
        assert submission.attributes.get("cliente_id") == cliente.id

        resposta = RespostaFormulario.query.filter_by(trabalho_id=submission.id).one()
        assert resposta.usuario_id is None
        assert resposta.evento_id == evento_id
