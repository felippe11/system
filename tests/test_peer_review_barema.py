import os
import sys
import types
from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
from werkzeug.security import generate_password_hash
from flask import Flask

from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

# Stub mercadopago before importing routes
mercadopago_stub = types.ModuleType("mercadopago")
mercadopago_stub.SDK = lambda *a, **k: None
sys.modules.setdefault("mercadopago", mercadopago_stub)

from extensions import db

from models import (
    Assignment,
    Cliente,
    Evento,
    EventoBarema,
    Review,
    Submission,
    Usuario,
)
from routes.peer_review_routes import peer_review_routes


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.secret_key = "test"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.build_engine_options("sqlite://")
    templates_path = Path(__file__).resolve().parent.parent / "templates"
    minimal_loader = DictLoader(
        {
            "base.html": "{% block content %}{% endblock %}",
            "partials/card.html": "{% macro render_card(title, body, description, classes='') %}<div class='card {{ classes }}'><h3>{{ title }}</h3>{{ body|safe }}</div>{% endmacro %}",
        }
    )

    app.jinja_loader = ChoiceLoader(
        [minimal_loader, app.jinja_loader, FileSystemLoader(str(templates_path))]
    )

    def _evento_home():
        return "home"

    app.add_url_rule(
        "/", endpoint="evento_routes.home", view_func=_evento_home
    )

    class _AnonUser:
        is_authenticated = False

    @app.context_processor
    def _inject_template_globals():
        return {
            "csrf_token": lambda: "",
            "current_user": _AnonUser(),
        }

    db.init_app(app)
    app.register_blueprint(peer_review_routes)
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome="Cli", email="cli@test", senha=generate_password_hash("123", method="pbkdf2:sha256"))
        db.session.add(cliente)
        db.session.flush()
        evento = Evento(cliente_id=cliente.id, nome="Evento", inscricao_gratuita=True)
        reviewer = Usuario(
            nome="Rev",
            cpf="1",
            email="rev@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
            formacao="X",
            tipo="professor",
        )
        db.session.add_all([evento, reviewer])
        db.session.flush()
        submission = Submission(
            title="T",
            content="Body",
            code_hash=generate_password_hash("code", method="pbkdf2:sha256"),
            evento_id=evento.id,
        )
        db.session.add(submission)
        db.session.flush()
        review = Review(
            submission_id=submission.id,
            reviewer_id=reviewer.id,
            locator="loc",
            access_code="12345678",
        )
        barema = EventoBarema(
            evento_id=evento.id, requisitos={"Qualidade": {"min": 1, "max": 5}}
        )
        db.session.add_all([review, barema])
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _get_review(app):
    with app.app_context():
        return Review.query.first()


def test_review_template_displays_barema_and_content(client, app):
    review = _get_review(app)
    resp = client.get(f"/review/{review.locator}")
    assert b"Body" in resp.data
    assert b"1 - 5" in resp.data
    assert b'min="1"' in resp.data
    assert b'max="5"' in resp.data


def test_review_rejects_score_out_of_range(client, app):
    review = _get_review(app)
    resp = client.post(
        f"/review/{review.locator}",
        data={"codigo": review.access_code, "Qualidade": "6"},
        follow_redirects=True,
    )
    with app.app_context():
        stored = Review.query.get(review.id)
        assert stored.scores is None


def test_review_accepts_valid_score(client, app):
    review = _get_review(app)
    resp = client.post(
        f"/review/{review.locator}",
        data={"codigo": review.access_code, "Qualidade": "3"},
        follow_redirects=True,
    )
    assert resp.status_code in (302, 200)
    with app.app_context():
        stored = Review.query.get(review.id)
        assert stored.scores == {"Qualidade": 3.0}
        assert stored.note == 3.0
