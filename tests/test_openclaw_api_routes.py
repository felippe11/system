import os

import pytest

os.environ.setdefault("SECRET_KEY", "testing")
os.environ.setdefault("DB_PASS", "testing")
os.environ.setdefault("GOOGLE_CLIENT_ID", "testing")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "testing")
os.environ.setdefault("OPENCLAW_API_TOKEN", "openclaw-test-token")
os.environ.setdefault("APP_BASE_URL", "https://api.example.test")

from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)
Config.OPENCLAW_API_ENABLED = True
Config.OPENCLAW_API_TOKEN = "openclaw-test-token"

from app import create_app
from extensions import db
from models import Evento, EventoInscricaoTipo, Inscricao, LoteInscricao, LoteTipoInscricao
from models.user import Cliente


FREE_EVENT_CPF = "52998224725"
PAID_EVENT_CPF = "11144477735"


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_ENGINE_OPTIONS=Config.build_engine_options("sqlite:///:memory:"),
        OPENCLAW_API_ENABLED=True,
        OPENCLAW_API_TOKEN="openclaw-test-token",
    )

    with app.app_context():
        db.create_all()

        cliente = Cliente(nome="Cliente API", email="cliente@example.com", senha="123")
        db.session.add(cliente)
        db.session.commit()

        free_event = Evento(
            cliente_id=cliente.id,
            nome="Evento Gratuito",
            descricao="Evento aberto",
            localizacao="Fortaleza",
            inscricao_gratuita=True,
            publico=True,
            status="ativo",
        )
        paid_event = Evento(
            cliente_id=cliente.id,
            nome="Evento Pago",
            descricao="Evento com pagamento",
            localizacao="Sobral",
            inscricao_gratuita=False,
            publico=True,
            status="ativo",
            habilitar_lotes=True,
        )
        db.session.add_all([free_event, paid_event])
        db.session.commit()

        tipo = EventoInscricaoTipo(
            evento_id=paid_event.id,
            nome="Participante Geral",
            preco=120.0,
        )
        db.session.add(tipo)
        db.session.commit()

        lote = LoteInscricao(evento_id=paid_event.id, nome="Lote 1", ativo=True)
        db.session.add(lote)
        db.session.commit()

        lote_tipo = LoteTipoInscricao(
            lote_id=lote.id,
            tipo_inscricao_id=tipo.id,
            preco=99.9,
        )
        db.session.add(lote_tipo)
        db.session.commit()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def _auth_headers():
    return {"Authorization": "Bearer openclaw-test-token"}


def test_requires_openclaw_token(client):
    response = client.get("/api/eventos")

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "authentication_failed"


def test_list_and_detail_events(client, app):
    response = client.get("/api/eventos", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert len(payload["data"]) == 2

    with app.app_context():
        paid_event = Evento.query.filter_by(nome="Evento Pago").first()

    detail = client.get(f"/api/eventos/{paid_event.id}", headers=_auth_headers())
    detail_payload = detail.get_json()

    assert detail.status_code == 200
    assert detail_payload["data"]["nome"] == "Evento Pago"
    assert len(detail_payload["data"]["tipos_inscricao"]) == 1
    assert len(detail_payload["data"]["lotes"]) == 1


def test_create_registration_lookup_status_and_receipt(client, app):
    with app.app_context():
        free_event = Evento.query.filter_by(nome="Evento Gratuito").first()

    create_payload = {
        "evento_id": free_event.id,
        "cpf": FREE_EVENT_CPF,
        "nome": "Ana API",
        "email": "ana@example.com",
        "formacao": "Graduacao",
    }
    response = client.post(
        "/api/inscricoes",
        headers=_auth_headers(),
        json=create_payload,
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    registration = payload["registration"]

    assert payload["created"] is True
    assert payload["payment_required"] is False
    assert registration["status_pagamento"] == "approved"

    lookup = client.get(
        f"/api/participantes/cpf/{FREE_EVENT_CPF}",
        headers=_auth_headers(),
    )
    assert lookup.status_code == 200
    assert lookup.get_json()["data"]["nome"] == "Ana API"

    by_cpf = client.get(
        f"/api/inscricoes?cpf={FREE_EVENT_CPF}",
        headers=_auth_headers(),
    )
    by_cpf_payload = by_cpf.get_json()["data"]
    assert len(by_cpf_payload["registrations"]) == 1

    status_response = client.get(
        f"/api/inscricoes/status/{registration['id']}",
        headers=_auth_headers(),
    )
    status_payload = status_response.get_json()["data"]
    assert status_payload["status_inscricao"] == "confirmada"
    assert status_payload["comprovante_disponivel"] is True

    receipt_response = client.get(
        f"/api/comprovantes/{registration['id']}",
        headers=_auth_headers(),
    )
    receipt_payload = receipt_response.get_json()["data"]
    assert receipt_payload["download_url"].startswith("https://api.example.test")

    receipt_path = (
        f"/api/comprovantes/{registration['id']}/arquivo"
        f"?token={receipt_payload['protocolo']}"
    )
    file_response = client.get(receipt_path)
    assert file_response.status_code == 200
    assert file_response.mimetype == "application/pdf"

    with app.app_context():
        saved = Inscricao.query.get(registration["id"])
        assert saved is not None
        assert saved.qr_code_token == receipt_payload["protocolo"]


def test_duplicate_registration_returns_conflict(client, app):
    with app.app_context():
        free_event = Evento.query.filter_by(nome="Evento Gratuito").first()

    payload = {
        "evento_id": free_event.id,
        "cpf": FREE_EVENT_CPF,
        "nome": "Ana API",
        "email": "ana@example.com",
        "formacao": "Graduacao",
    }
    first = client.post("/api/inscricoes", headers=_auth_headers(), json=payload)
    second = client.post("/api/inscricoes", headers=_auth_headers(), json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    error = second.get_json()["error"]
    assert error["code"] == "duplicate_registration"
    assert error["details"]["registration"]["usuario"]["cpf"] == "529.982.247-25"


def test_generate_payment_link(client, app, monkeypatch):
    with app.app_context():
        paid_event = Evento.query.filter_by(nome="Evento Pago").first()
        tipo = EventoInscricaoTipo.query.filter_by(evento_id=paid_event.id).first()
        lote = LoteInscricao.query.filter_by(evento_id=paid_event.id).first()

    payload = {
        "evento_id": paid_event.id,
        "cpf": PAID_EVENT_CPF,
        "nome": "Bruno API",
        "email": "bruno@example.com",
        "formacao": "Pos-Graduacao",
        "tipo_inscricao_id": tipo.id,
        "lote_id": lote.id,
    }
    create = client.post("/api/inscricoes", headers=_auth_headers(), json=payload)
    registration_id = create.get_json()["data"]["registration"]["id"]

    class FakePreferenceClient:
        def create(self, preference_data):
            assert preference_data["external_reference"] == str(registration_id)
            return {"response": {"init_point": "https://pay.example.test/session/123"}}

    class FakeSdk:
        def preference(self):
            return FakePreferenceClient()

    monkeypatch.setattr("services.openclaw_api_service.get_sdk", lambda: FakeSdk())

    response = client.post(
        "/api/pagamentos/gerar-link",
        headers=_auth_headers(),
        json={"inscricao_id": registration_id},
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["payment_required"] is True
    assert payload["payment_url"] == "https://pay.example.test/session/123"

    with app.app_context():
        saved = Inscricao.query.get(registration_id)
        assert saved.boleto_url == "https://pay.example.test/session/123"
