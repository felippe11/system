import io
import pandas as pd
import pytest
import os

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "y")
os.environ.setdefault("DB_PASS", "test")

from flask import Flask
from config import Config
from extensions import db, login_manager, csrf
from models.material import Polo
from models.user import Cliente
from routes.material_routes import material_routes


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.build_engine_options(
        "sqlite://"
    )
    login_manager.init_app(app)
    db.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(material_routes)

    @login_manager.user_loader
    def load_user(user_id):
        return Cliente.query.get(int(user_id))

    with app.app_context():
        db.create_all()
        cliente = Cliente(nome="Cli", email="cli@test", senha="123")
        db.session.add(cliente)
        db.session.commit()
        polo = Polo(nome="Polo 1", cliente_id=cliente.id)
        db.session.add(polo)
        db.session.commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)


def test_criar_material_com_preco_e_gerar_relatorio(app, client):
    with app.app_context():
        cliente = Cliente.query.first()
        polo = Polo.query.first()

    login(client, cliente.id)

    resp = client.post(
        "/api/materiais",
        json={
            "polo_id": polo.id,
            "nome": "Papel",
            "unidade": "un",
            "quantidade_inicial": 5,
            "quantidade_minima": 1,
            "preco_unitario": 2.5,
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["material"]["preco_unitario"] == 2.5
    assert data["material"]["data_atualizacao"] is not None

    resp = client.get("/relatorio", query_string={"polo_id": polo.id})
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    df = pd.read_excel(io.BytesIO(resp.data), sheet_name="Materiais")
    assert float(df.loc[0, "Preço Unitário"]) == pytest.approx(2.5)
    assert df.loc[0, "Última Atualização"] != ""

