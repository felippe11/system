import io
import json
import os
import pandas as pd
import pytest
from extensions import db
from models import WorkMetadata, Submission
from sqlalchemy.exc import DataError


def make_excel():
    df = pd.DataFrame(
        {
            "titulo": ["T1"],
            "categoria": ["C1"],
            "rede_ensino": ["Rede1"],
            "etapa_ensino": ["Etapa1"],
            "pdf_url": ["http://example.com/doc.pdf"],
            "resumo": ["R1"],
            "extra": ["E1"],
        }
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer, df


def make_excel_sem_titulo():
    df = pd.DataFrame(
        {
            "categoria": ["C1"],
            "resumo": ["R1"],
        }
    )
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


def test_upload_and_persist(client, app):
    excel, df = make_excel()
    evento_id = 123
    resp = client.post(
        "/importar_trabalhos",
        data={"arquivo": (excel, "dados.xlsx"), "evento_id": evento_id},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert b"titulo" in resp.data
    assert b"categoria" in resp.data
    data_json = df.to_dict(orient="records")
    with app.app_context():
        subs = Submission.query.all()
        assert len(subs) == 1
        assert subs[0].evento_id == evento_id
        assert subs[0].attributes == data_json[0]

    resp = client.post(
        "/importar_trabalhos",
        data={"data": json.dumps(data_json), "evento_id": evento_id},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        rows = WorkMetadata.query.all()
        assert len(rows) == 1
        row = rows[0]
        assert row.evento_id == evento_id
        assert row.titulo == "T1"
        assert row.categoria == "C1"
        assert row.rede_ensino == "Rede1"
        assert row.etapa_ensino == "Etapa1"
        assert row.pdf_url == "http://example.com/doc.pdf"
        assert row.data == data_json[0]


def test_upload_sem_titulo(client, app):
    excel, df = make_excel_sem_titulo()
    evento_id = 456
    resp = client.post(
        "/importar_trabalhos",
        data={"arquivo": (excel, "dados.xlsx"), "evento_id": evento_id},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data_json = df.to_dict(orient="records")
    with app.app_context():
        subs = Submission.query.all()
        assert len(subs) == 1
        assert subs[0].title == "C1"
        assert subs[0].attributes == data_json[0]

    resp = client.post(
        "/importar_trabalhos",
        data={"data": json.dumps(data_json), "evento_id": evento_id},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        rows = WorkMetadata.query.all()
        assert len(rows) == 1
        row = rows[0]
        assert row.titulo is None
        assert row.categoria == "C1"
        assert row.data == data_json[0]


def test_oversize_field_returns_error(client, app, monkeypatch):
    evento_id = 789
    data_json = [{"titulo": "x" * 300}]

    class MockOrig(Exception):
        def __init__(self):
            self.diag = type("Diag", (), {"column_name": "titulo"})()

    def fake_commit():
        raise DataError("stmt", {}, MockOrig())

    called = {"rollback": False}

    def fake_rollback():
        called["rollback"] = True

    monkeypatch.setattr(db.session, "commit", fake_commit)
    monkeypatch.setattr(db.session, "rollback", fake_rollback)

    resp = client.post(
        "/importar_trabalhos",
        data={"data": json.dumps(data_json), "evento_id": evento_id},
        follow_redirects=True,
    )
    assert resp.status_code == 400
    body = json.loads(resp.data)
    assert "titulo" in body["error"]
    assert called["rollback"]
