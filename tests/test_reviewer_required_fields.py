import os
from jinja2 import ChoiceLoader, DictLoader
from werkzeug.security import generate_password_hash
import pytest

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "y")
os.environ.setdefault("DB_PASS", "test")

from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from flask import Flask
from extensions import db, login_manager, migrate
from flask_migrate import upgrade

from models import Cliente, Formulario, CampoFormulario
from routes.revisor_routes import revisor_routes


@pytest.fixture
def app():
    templates_path = os.path.join(os.path.dirname(__file__), "..", "templates")
    app = Flask(__name__, template_folder=templates_path)
    app.jinja_loader = ChoiceLoader(
        [DictLoader({"base.html": "{% block content %}{% endblock %}"}), app.jinja_loader]
    )
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.build_engine_options("sqlite://")
    app.jinja_env.globals["csrf_token"] = lambda: ""

    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Cliente.query.get(int(user_id))

    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(revisor_routes)

    with app.app_context():
        try:
            upgrade(revision="heads")
        except SystemExit:
            db.create_all()
        cliente = Cliente(
            nome="Cli",
            email="cli@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
        )
        db.session.add(cliente)
        db.session.commit()
        form = Formulario(nome="Form", cliente_id=cliente.id)
        db.session.add(form)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_config_revisor_adds_default_fields(app, client):
    """Configuring a reviewer process adds required name and email fields."""
    from flask_login import login_user, logout_user

    with app.app_context():
        cliente = Cliente.query.filter_by(email="cli@test").first()
        formulario = Formulario.query.filter_by(cliente_id=cliente.id).first()
        assert CampoFormulario.query.filter_by(formulario_id=formulario.id).count() == 0

        with client:
            with app.test_request_context():
                login_user(cliente)
            resp = client.post(
                "/config_revisor",
                data={
                    "formulario_id": formulario.id,
                    "num_etapas": 1,
                    "stage_name": ["Etapa 1"],
                },
            )
            with app.test_request_context():
                logout_user()

        assert resp.status_code in (200, 302)
        campos = CampoFormulario.query.filter_by(formulario_id=formulario.id).all()
        campos = {c.nome: c for c in campos}
        assert {"nome", "email"} <= set(campos)
        assert campos["nome"].obrigatorio is True
        assert campos["email"].obrigatorio is True

