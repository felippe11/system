import io
import os

import pandas as pd
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
from models.event import (
    CampoFormulario,
    Evento,
    Formulario,
    RespostaCampoFormulario,
    RespostaFormulario,
)
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


def test_importar_trabalhos_excel(client, app):
    login(client)

    with app.app_context():
        cliente = Cliente.query.filter_by(email="cli@test").first()
        formulario = Formulario(
            nome="Formul\u00e1rio de Trabalhos", cliente_id=cliente.id
        )
        db.session.add(formulario)
        db.session.flush()

        campo_titulo = CampoFormulario(
            formulario_id=formulario.id,
            nome="T\u00edtulo",
            tipo="text",
            obrigatorio=True,
        )
        campo_categoria = CampoFormulario(
            formulario_id=formulario.id,
            nome="Categoria",
            tipo="text",
            obrigatorio=False,
        )
        evento = Evento(cliente_id=cliente.id, nome="Evento Importa\u00e7\u00e3o")

        db.session.add_all([campo_titulo, campo_categoria, evento])
        db.session.commit()
        evento_id = evento.id

    df = pd.DataFrame(
        {
            "T\u00edtulo": ["Trabalho Exemplo", None],
            "Categoria": ["Educa\u00e7\u00e3o", None],
        }
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)

    response = client.post(
        "/trabalhos/importar",
        data={
            "evento_id": evento_id,
            "arquivo_excel": (buffer, "trabalhos.xlsx"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        submissions = Submission.query.all()
        assert len(submissions) == 1
        assert submissions[0].title == "Trabalho Exemplo"
        assert submissions[0].evento_id == evento_id

        respostas = RespostaFormulario.query.all()
        assert len(respostas) == 1
        respostas_campos = RespostaCampoFormulario.query.all()
        assert len(respostas_campos) == 2

        valores = {
            resp_campo.campo.nome: resp_campo.valor
            for resp_campo in respostas_campos
        }
        assert valores["T\u00edtulo"] == "Trabalho Exemplo"
        assert valores["Categoria"] == "Educa\u00e7\u00e3o"
