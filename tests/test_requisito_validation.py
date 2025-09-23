import os
import pytest
from flask import Flask
from jinja2 import ChoiceLoader, DictLoader
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")

from config import Config
from extensions import db, login_manager, csrf
from models import (
    Cliente,
    Formulario,
    RevisorProcess,
    ProcessoBarema,
    ProcessoBaremaRequisito,
)
from routes.revisor_routes import revisor_routes

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)


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

    @login_manager.user_loader
    def load_user(user_id):  # pragma: no cover
        return Cliente.query.get(int(user_id))

    db.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(revisor_routes)
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome="C",
            email="c@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
        )
        db.session.add(cliente)
        db.session.commit()
        form = Formulario(nome="F", cliente_id=cliente.id)
        db.session.add(form)
        db.session.commit()
        proc = RevisorProcess(
            cliente_id=cliente.id,
            formulario_id=form.id,
            num_etapas=1,
            nome="Proc",
            status="ativo",
        )
        db.session.add(proc)
        db.session.commit()
        barema = ProcessoBarema(process_id=proc.id)
        db.session.add(barema)
        db.session.commit()
        requisito = ProcessoBaremaRequisito(
            barema_id=barema.id,
            nome="R",
            pontuacao_min=0,
            pontuacao_max=10,
        )
        db.session.add(requisito)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_add_requisito_invalid_range(client, app):
    with client:
        with app.app_context():
            cliente = Cliente.query.first()
            barema = ProcessoBarema.query.first()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(cliente.id)
            sess['_fresh'] = True
        resp = client.post(
            f"/revisor/barema/{barema.id}/requisito/new",
            data={
                "nome": "X",
                "descricao": "Y",
                "pontuacao_min": 5,
                "pontuacao_max": 4,
            },
        )
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Pontuação mínima" in html
        with app.app_context():
            count = ProcessoBaremaRequisito.query.filter_by(
                barema_id=barema.id, nome="X"
            ).count()
            assert count == 0


def test_edit_requisito_invalid_range(client, app):
    with client:
        with app.app_context():
            requisito = ProcessoBaremaRequisito.query.first()
            cliente = Cliente.query.first()
            original_min = float(requisito.pontuacao_min)
            original_max = float(requisito.pontuacao_max)
        with client.session_transaction() as sess:
            sess['_user_id'] = str(cliente.id)
            sess['_fresh'] = True
        resp = client.post(
            f"/revisor/requisito/{requisito.id}/edit",
            data={
                "nome": requisito.nome,
                "descricao": requisito.descricao,
                "pontuacao_min": original_max + 1,
                "pontuacao_max": original_max,
            },
        )
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Pontuação mínima" in html
        with app.app_context():
            atualizado = ProcessoBaremaRequisito.query.get(requisito.id)
            assert float(atualizado.pontuacao_min) == original_min
            assert float(atualizado.pontuacao_max) == original_max
