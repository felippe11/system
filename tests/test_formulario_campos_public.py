import os
import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "y")
os.environ.setdefault("DB_PASS", "test")

from config import Config
from extensions import db, login_manager
from models import Formulario, CampoFormulario
from models.user import Cliente
from models.review import RevisorProcess
from routes.revisor_routes import revisor_routes

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.build_engine_options("sqlite://")
    app.secret_key = "test"

    db.init_app(app)
    login_manager.init_app(app)
    app.register_blueprint(revisor_routes)

    @login_manager.user_loader
    def load_user(user_id):  # pragma: no cover
        return Cliente.query.get(int(user_id))

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
        campo = CampoFormulario(
            formulario_id=form.id,
            nome="campo1",
            tipo="text",
        )
        db.session.add(campo)
        db.session.commit()
        proc = RevisorProcess(
            cliente_id=cliente.id,
            formulario_id=form.id,
            num_etapas=1,
            nome="Proc",
            status="ativo",
            exibir_para_participantes=True,
        )
        db.session.add(proc)
        db.session.commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_public_can_load_campos(client, app):
    with app.app_context():
        form = Formulario.query.first()
        form_id = form.id
    resp = client.get(f"/api/formulario/{form_id}/campos")
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(campo["nome"] == "campo1" for campo in data)
