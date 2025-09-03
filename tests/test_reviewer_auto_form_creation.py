import os
import pytest
from werkzeug.security import generate_password_hash
from flask import Flask
from jinja2 import ChoiceLoader, DictLoader
from flask_migrate import upgrade

from config import Config
from extensions import db, login_manager, migrate
from models import Cliente, Formulario, RevisorProcess
from routes.revisor_routes import revisor_routes

os.environ.setdefault("DB_PASS", "test")


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
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_config_revisor_creates_basic_form(app, client):
    """Posting without formulario_id creates a basic form automatically."""
    from flask_login import login_user, logout_user

    with app.app_context():
        cliente = Cliente.query.filter_by(email="cli@test").first()
        assert Formulario.query.filter_by(cliente_id=cliente.id).count() == 0

        with client:
            with app.test_request_context():
                login_user(cliente)
            resp = client.post(
                "/revisor/processos",
                data={"formulario_id": "", "num_etapas": 1, "stage_name": ["Etapa 1"]},
            )
            with app.test_request_context():
                logout_user()

        assert resp.status_code == 201
        proc_id = resp.get_json()["id"]
        form = Formulario.query.filter_by(cliente_id=cliente.id).first()
        assert form is not None
        campos = {c.nome: c for c in form.campos}
        assert {"nome", "email"} <= set(campos)
        assert campos["nome"].obrigatorio is True
        assert campos["email"].obrigatorio is True
        proc = RevisorProcess.query.get(proc_id)
        assert proc is not None and proc.formulario_id == form.id
