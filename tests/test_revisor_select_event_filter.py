import os
from datetime import date, timedelta
import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")
from config import Config
from flask import Flask, get_flashed_messages
from extensions import db, login_manager, csrf
from models import Cliente, Formulario, RevisorProcess, Evento
from routes.revisor_routes import revisor_routes, select_event
from flask import Blueprint
from unittest.mock import patch

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)


@pytest.fixture
def app():
    templates_path = os.path.join(os.path.dirname(__file__), "..", "templates")
    app = Flask(__name__, template_folder=templates_path)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.build_engine_options("sqlite://")
    login_manager.init_app(app)

    @login_manager.user_loader
    def _load_user(user_id):  # pragma: no cover
        return None

    db.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(revisor_routes)
    evento_routes = Blueprint("evento_routes", __name__)

    @evento_routes.route("/")
    def home():  # pragma: no cover
        return "home"

    app.register_blueprint(evento_routes)
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome="C", email="c@test", senha=generate_password_hash("123"))
        db.session.add(cliente)
        db.session.commit()
        form = Formulario(nome="F", cliente_id=cliente.id)
        db.session.add(form)
        db.session.commit()
        linked_direct = Evento(
            cliente_id=cliente.id,
            nome="LinkedDirect",
            inscricao_gratuita=True,
            publico=True,
            status="ativo",
        )
        linked_assoc = Evento(
            cliente_id=cliente.id,
            nome="LinkedAssoc",
            inscricao_gratuita=True,
            publico=True,
            status="ativo",
        )
        unlinked = Evento(
            cliente_id=cliente.id,
            nome="Unlinked",
            inscricao_gratuita=True,
            publico=True,
            status="ativo",
        )
        inactive = Evento(
            cliente_id=cliente.id,
            nome="Inactive",
            inscricao_gratuita=True,
            publico=True,
            status="ativo",
        )
        db.session.add_all([linked_direct, linked_assoc, unlinked, inactive])
        db.session.commit()
        proc_direct = RevisorProcess(
            cliente_id=cliente.id,
            formulario_id=form.id,
            num_etapas=1,
            availability_start=date.today() - timedelta(days=1),
            availability_end=date.today() + timedelta(days=1),
            exibir_para_participantes=True,
            evento_id=linked_direct.id,
        )
        proc_assoc = RevisorProcess(
            cliente_id=cliente.id,
            formulario_id=form.id,
            num_etapas=1,
            availability_start=date.today() - timedelta(days=1),
            availability_end=date.today() + timedelta(days=1),
            exibir_para_participantes=True,
        )
        proc_inactive = RevisorProcess(
            cliente_id=cliente.id,
            formulario_id=form.id,
            num_etapas=1,
            availability_start=date.today() - timedelta(days=3),
            availability_end=date.today() - timedelta(days=1),
            exibir_para_participantes=True,
            evento_id=inactive.id,
        )
        db.session.add_all([proc_direct, proc_assoc, proc_inactive])
        db.session.commit()
        proc_assoc.eventos.append(linked_assoc)
        db.session.commit()
    yield app


def test_only_linked_events_are_listed(app):
    with app.test_request_context("/processo_seletivo"):
        with patch("routes.revisor_routes.render_template") as rt:
            rt.side_effect = lambda tpl, **ctx: ctx
            ctx = select_event()
    eventos = [item["evento"].nome for item in ctx["eventos"]]
    assert "LinkedDirect" in eventos
    assert "LinkedAssoc" in eventos
    assert "Unlinked" not in eventos
    assert "Inactive" not in eventos


def test_select_event_no_processes_flash(app):
    with app.app_context():
        RevisorProcess.query.delete()
        db.session.commit()
    with app.test_request_context("/processo_seletivo"):
        with patch("routes.revisor_routes.render_template") as rt:
            rt.side_effect = lambda tpl, **ctx: ctx
            ctx = select_event()
        flashes = get_flashed_messages(with_categories=True)
    assert ctx["eventos"] == []
    assert (
        "info",
        "Nenhum processo seletivo de revisores disponível no momento.",
    ) in flashes
