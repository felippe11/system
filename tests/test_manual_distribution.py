from datetime import datetime
import os

os.environ.setdefault("GOOGLE_CLIENT_ID", "test")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test")
os.environ.setdefault("MAILJET_API_KEY", "test")
os.environ.setdefault("MAILJET_SECRET_KEY", "test")
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("DB_PASS", "postgres")
os.environ.setdefault("MERCADOPAGO_ACCESS_TOKEN", "test")

import pytest
import sqlalchemy as sa

from routes.trabalho_routes import _detect_assignment_columns


@pytest.fixture(scope="function")
def manual_distribution_app(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test")
    monkeypatch.setenv("MAILJET_API_KEY", "test")
    monkeypatch.setenv("MAILJET_SECRET_KEY", "test")
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DB_PASS", "postgres")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "test")

    db_path = tmp_path / "manual_distribution.db"
    database_uri = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", database_uri)

    from config import Config

    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", database_uri, raising=False)
    monkeypatch.setattr(
        Config,
        "SQLALCHEMY_ENGINE_OPTIONS",
        Config.build_engine_options(database_uri),
        raising=False,
    )

    from app import create_app
    from extensions import db
    from models.event import RespostaFormulario

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        db.create_all()
        if not RespostaFormulario.query.get(1):
            db.session.add(RespostaFormulario(id=1))
            db.session.commit()
        inspector = sa.inspect(db.engine)
        available_columns = [col['name'] for col in inspector.get_columns('assignment')]
        if not available_columns:
            raise RuntimeError('assignment table not created in test database')

    yield app

    with app.app_context():
        db.drop_all()


def _post_manual_distribution(app, payload):
    client = app.test_client()
    return client.post("/api/distribution/manual", json=payload)


def _base_payload():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return {
        "work_ids": [1],
        "assignments": [
            {
                "workId": 1,
                "reviewerId": 10,
            }
        ],
        "deadline": today,
        "notes": "Teste de distribuição",
    }


def test_detect_assignment_columns_with_aliases():
    table = sa.Table(
        'assignment',
        sa.MetaData(),
        sa.Column('submission_id', sa.Integer),
        sa.Column('reviewer', sa.Integer),
    )

    resolved, column_map = _detect_assignment_columns(table)
    assert resolved['resposta'].name == 'submission_id'
    assert resolved['reviewer'].name == 'reviewer'
    assert resolved['deadline'] is None
    assert sorted(column_map.keys()) == ['reviewer', 'submission_id']


def test_detect_assignment_columns_with_default_names():
    table = sa.Table(
        'assignment',
        sa.MetaData(),
        sa.Column('resposta_formulario_id', sa.Integer),
        sa.Column('reviewer_id', sa.Integer),
        sa.Column('notes', sa.Text),
    )

    resolved, _ = _detect_assignment_columns(table)
    assert resolved['resposta'].name == 'resposta_formulario_id'
    assert resolved['reviewer'].name == 'reviewer_id'
    assert resolved['notes'].name == 'notes'


def test_manual_distribution_route_with_default_schema(manual_distribution_app):
    response = _post_manual_distribution(manual_distribution_app, _base_payload())
    assert response.status_code == 200, response.get_json()

    from extensions import db

    with manual_distribution_app.app_context():
        rows = db.session.execute(
            sa.text("SELECT resposta_formulario_id, reviewer_id FROM assignment")
        ).fetchall()
        assert rows == [(1, 10)]
