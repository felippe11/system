import os

import pytest
from flask import Flask
from jinja2 import ChoiceLoader, DictLoader
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "y")
os.environ.setdefault("DB_PASS", "test")

from config import Config
from extensions import csrf, db, login_manager
from models import (
    Cliente,
    RevisorCandidatura,
    RevisorCandidaturaEtapa,
    RevisorCriterio,
    RevisorEtapa,
    RevisorProcess,
)
from routes.revisor_routes import revisor_routes


@pytest.fixture
def app():
    templates_path = os.path.join(os.path.dirname(__file__), "..", "templates")
    app = Flask(__name__, template_folder=templates_path)
    app.jinja_loader = ChoiceLoader([
        DictLoader({"base.html": "{% block content %}{% endblock %}"}),
        app.jinja_loader,
    ])
    app.config.update(
        TESTING=True,
        SECRET_KEY="test",
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_ENGINE_OPTIONS=Config.build_engine_options("sqlite://"),
    )
    login_manager.init_app(app)

    @login_manager.user_loader  # pragma: no cover
    def load_user(user_id):
        return Cliente.query.get(int(user_id))

    db.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(revisor_routes)

    with app.app_context():
        db.create_all()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_delete_process_removes_related_data(app, client):
    with app.app_context():
        cliente = Cliente(
            nome="Cli",
            email="cli@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
        )
        db.session.add(cliente)
        db.session.commit()
        proc = RevisorProcess(
            cliente_id=cliente.id,
            num_etapas=1,
            nome="Proc",
            status="ativo",
        )
        db.session.add(proc)
        db.session.commit()
        etapa = RevisorEtapa(process_id=proc.id, numero=1, nome="E1")
        criterio = RevisorCriterio(process_id=proc.id, nome="C1")
        cand = RevisorCandidatura(
            process_id=proc.id, nome="Cand", email="cand@test"
        )
        db.session.add_all([etapa, criterio, cand])
        db.session.commit()
        status = RevisorCandidaturaEtapa(candidatura_id=cand.id, etapa_id=etapa.id)
        db.session.add(status)
        db.session.commit()

    with client:
        with client.session_transaction() as sess:
            sess["_user_id"] = str(cliente.id)
            sess["_fresh"] = True
        resp = client.post(f"/revisor/{proc.id}/delete")
        assert resp.status_code == 302

    with app.app_context():
        assert RevisorProcess.query.get(proc.id) is None
        assert RevisorEtapa.query.count() == 0
        assert RevisorCriterio.query.count() == 0
        assert RevisorCandidatura.query.count() == 0
        assert RevisorCandidaturaEtapa.query.count() == 0

