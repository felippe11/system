import os
import pytest
from werkzeug.security import generate_password_hash

os.environ["SECRET_KEY"] = "test-key"
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")
from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db

    Cliente,
    Formulario,
    CampoFormulario,
    Usuario,
    RespostaFormulario,
    RespostaCampo,
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

        form1 = Formulario(nome="F1", cliente_id=cliente.id)
        form2 = Formulario(nome="F2", cliente_id=cliente.id)
        db.session.add_all([form1, form2])
        db.session.commit()

        campo1 = CampoFormulario(formulario_id=form1.id, nome="C1", tipo="texto")
        campo2 = CampoFormulario(formulario_id=form2.id, nome="C2", tipo="texto")
        db.session.add_all([campo1, campo2])
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

        rf1 = RespostaFormulario(formulario_id=form1.id, usuario_id=usuario.id)
        rf2 = RespostaFormulario(formulario_id=form1.id, usuario_id=usuario.id)
        rf3 = RespostaFormulario(formulario_id=form2.id, usuario_id=usuario.id)
        db.session.add_all([rf1, rf2, rf3])
        db.session.commit()

        rc1 = RespostaCampo(
            resposta_formulario_id=rf1.id, campo_id=campo1.id, valor="a"
        )
        rc2 = RespostaCampo(
            resposta_formulario_id=rf2.id, campo_id=campo1.id, valor="b"
        )
        rc3 = RespostaCampo(
            resposta_formulario_id=rf3.id, campo_id=campo2.id, valor="c"
        )
        db.session.add_all([rc1, rc2, rc3])
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        "/login", data={"email": "cli@test", "senha": "123"}, follow_redirects=False
    )


def test_delete_formulario_removes_only_related_rows(client, app):
    login(client)
    with app.app_context():
        form1 = Formulario.query.filter_by(nome="F1").first()
        form2 = Formulario.query.filter_by(nome="F2").first()

    resp = client.post(f"/formularios/{form1.id}/excluir")
    assert resp.status_code in {302, 200}

    with app.app_context():
        assert Formulario.query.get(form1.id) is None
        assert Formulario.query.get(form2.id) is not None

        assert RespostaFormulario.query.filter_by(formulario_id=form1.id).count() == 0
        assert RespostaFormulario.query.filter_by(formulario_id=form2.id).count() == 1

        assert RespostaCampo.query.count() == 1
        remaining = RespostaCampo.query.first()
        assert remaining.resposta_formulario.formulario_id == form2.id
