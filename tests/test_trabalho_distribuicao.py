import io
import json
import os

import pandas as pd
import pytest

from extensions import db
from models import WorkMetadata


def make_excel():
    df = pd.DataFrame({"titulo": ["T1"], "resumo": ["R1"], "extra": ["E1"]})
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer, df


@pytest.fixture
def app():
    os.environ.setdefault("SECRET_KEY", "test")
    os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
    os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")
    os.environ.setdefault("DB_ONLINE", "sqlite:///:memory:")
    os.environ.setdefault("DB_PASS", "test")
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["LOGIN_DISABLED"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_distribuicao_flow(client, app):
    excel, df = make_excel()
    resp = client.post(
        "/distribuicao",
        data={"arquivo": (excel, "dados.xlsx")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert b"titulo" in resp.data
    assert b"resumo" in resp.data

    data_json = df.to_dict(orient="records")
    resp = client.post(
        "/distribuicao",
        data={
            "data": json.dumps(data_json),
            "map_titulo": "titulo",
            "map_resumo": "resumo",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Dados importados com sucesso" in resp.data
    with app.app_context():
        rows = WorkMetadata.query.all()
        assert len(rows) == 1
        assert rows[0].data == {"titulo": "T1", "resumo": "R1"}

