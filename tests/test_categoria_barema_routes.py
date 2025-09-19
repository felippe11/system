import os
import sys
import types

import pytest
from flask_login import login_user, logout_user
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")
os.environ.setdefault("DB_PASS", "test")

mercadopago_stub = types.ModuleType("mercadopago")
mercadopago_stub.SDK = lambda *args, **kwargs: None
sys.modules.setdefault("mercadopago", mercadopago_stub)

from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options("sqlite://")

from app import create_app
from extensions import db
from models.user import Usuario, Cliente
from models.event import (
    Evento,
    Formulario,
    CampoFormulario,
    RespostaFormulario,
    RespostaCampo,
)
from models.review import Submission, Assignment, Review, CategoriaBarema


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(
        "models.formulario.ensure_formulario_trabalhos",
        lambda: None,
    )

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()

        cliente = Cliente(
            nome="Cliente",
            email="cliente@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
        )
        db.session.add(cliente)
        db.session.flush()

        reviewer = Usuario(
            nome="Revisor",
            cpf="111",
            email="rev@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
            formacao="Formação",
            tipo="revisor",
        )
        db.session.add(reviewer)

        evento = Evento(
            cliente_id=cliente.id,
            nome="Evento",
            inscricao_gratuita=True,
        )
        db.session.add(evento)
        db.session.flush()

        formulario = Formulario(
            nome="Formulário Categoria",
            cliente_id=cliente.id,
        )
        campo_categoria = CampoFormulario(
            formulario=formulario,
            nome="Categoria",
            tipo="text",
            obrigatorio=True,
        )
        submission = Submission(
            title="Trabalho",
            content="Conteúdo",
            code_hash=generate_password_hash("code", method="pbkdf2:sha256"),
            evento_id=evento.id,
        )
        db.session.add_all([formulario, campo_categoria, submission])
        db.session.flush()

        resposta = RespostaFormulario(
            formulario_id=formulario.id,
            trabalho_id=submission.id,
            evento_id=evento.id,
        )
        db.session.add(resposta)
        db.session.flush()

        resposta_campo = RespostaCampo(
            resposta_formulario_id=resposta.id,
            campo_id=campo_categoria.id,
            valor="Poster",
        )
        assignment = Assignment(
            resposta_formulario_id=resposta.id,
            reviewer_id=reviewer.id,
        )
        review = Review(
            submission_id=submission.id,
            reviewer_id=reviewer.id,
            locator="categoria-loc",
            access_code="123456",
        )
        barema = CategoriaBarema(
            evento_id=evento.id,
            categoria="Poster",
            nome="Barema Poster",
            criterios={
                "Clareza": {
                    "descricao": "Avalia clareza da apresentação",
                    "max": 5,
                },
                "Impacto": {
                    "min": 2,
                    "max": 10,
                },
            },
        )
        db.session.add_all([resposta_campo, assignment, review, barema])
        db.session.flush()

        assignment_check = (
            db.session.query(Assignment)
            .join(
                RespostaFormulario,
                Assignment.resposta_formulario_id == RespostaFormulario.id,
            )
            .filter(
                RespostaFormulario.trabalho_id == submission.id,
                Assignment.reviewer_id == reviewer.id,
            )
            .first()
        )
        assert assignment_check is not None

        db.session.commit()

        import routes.revisor_routes as revisor_routes_module
        import routes.peer_review_routes as peer_review_routes_module

        globals()["revisor_routes"] = revisor_routes_module
        globals()["peer_review_routes"] = peer_review_routes_module
        monkeypatch.setattr(
            peer_review_routes_module,
            "RespostaCampo",
            RespostaCampo,
        )
        monkeypatch.setattr(
            peer_review_routes_module,
            "CampoFormulario",
            CampoFormulario,
        )

        class _AssignmentQueryWrapper:
            def __init__(self, query):
                self._query = query

            def join(self, *args, **kwargs):
                return _AssignmentQueryWrapper(self._query.join(*args, **kwargs))

            def filter(self, *args, **kwargs):
                return _AssignmentQueryWrapper(self._query.filter(*args, **kwargs))

            def filter_by(self, **kwargs):
                kwargs.pop("submission_id", None)
                return _AssignmentQueryWrapper(self._query.filter_by(**kwargs))

            def first(self):
                return self._query.first()

            def first_or_404(self):
                return self._query.first_or_404()

        assignment_query_wrapper = _AssignmentQueryWrapper(Assignment.query)

        monkeypatch.setattr(
            revisor_routes_module.Assignment,
            "query",
            assignment_query_wrapper,
        )
        monkeypatch.setattr(
            peer_review_routes_module.Assignment,
            "query",
            assignment_query_wrapper,
        )

    yield app

    with app.app_context():
        db.drop_all()


def _as_text(response):
    return response.get_data(as_text=True) if hasattr(response, "get_data") else response


def test_revisor_categoria_barema_get(app):
    with app.app_context():
        submission = Submission.query.first()
        reviewer = Usuario.query.filter_by(email="rev@test").first()

    with app.test_request_context(f"/revisor/avaliar/{submission.id}", method="GET"):
        login_user(reviewer)
        assert (
            CategoriaBarema.query.filter_by(
                evento_id=submission.evento_id, categoria="Poster"
            ).first()
            is not None
        )
        html = _as_text(revisor_routes.avaliar(submission.id))
        logout_user()

    assert "Clareza" in html
    assert 'min="0"' in html
    assert 'max="5"' in html
    assert 'min="2"' in html
    assert 'max="10"' in html


def test_revisor_categoria_barema_post(app):
    with app.app_context():
        submission = Submission.query.first()
        reviewer = Usuario.query.filter_by(email="rev@test").first()

    with app.test_request_context(
        f"/revisor/avaliar/{submission.id}",
        method="POST",
        data={"Clareza": "3", "Impacto": "8"},
    ):
        login_user(reviewer)
        response = revisor_routes.avaliar(submission.id)
        logout_user()

    assert response.status_code == 302

    with app.app_context():
        stored = Review.query.filter_by(
            submission_id=submission.id,
            reviewer_id=reviewer.id,
        ).first()
        assert stored is not None
        assert stored.scores == {"Clareza": 3, "Impacto": 8}


def test_peer_review_categoria_barema_get(app):
    with app.app_context():
        review = Review.query.filter_by(locator="categoria-loc").first()

    with app.test_request_context(f"/review/{review.locator}", method="GET"):
        html = _as_text(peer_review_routes.review_form(review.locator))

    assert "Clareza" in html
    assert 'min="0"' in html
    assert 'max="5"' in html
    assert 'min="2"' in html
    assert 'max="10"' in html


def test_peer_review_categoria_barema_post(app):
    with app.app_context():
        review = Review.query.filter_by(locator="categoria-loc").first()

    with app.test_request_context(
        f"/review/{review.locator}",
        method="POST",
        data={"codigo": review.access_code, "Clareza": "4", "Impacto": "6"},
    ):
        response = peer_review_routes.review_form(review.locator)

    assert response.status_code == 302

    with app.app_context():
        stored = Review.query.get(review.id)
        assert stored is not None
        assert stored.scores == {"Clareza": 4.0, "Impacto": 6.0}
        assert stored.note == 10.0
