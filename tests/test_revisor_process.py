import os
import sys
import types
import pytest
from werkzeug.security import generate_password_hash
from config import Config

# Stubs to avoid heavy optional dependencies
mercadopago_stub = types.ModuleType('mercadopago')
mercadopago_stub.SDK = lambda *a, **k: None
sys.modules.setdefault('mercadopago', mercadopago_stub)
pdf_stub = types.ModuleType('services.pdf_service')
pdf_stub.gerar_pdf_respostas = lambda *a, **k: None
pdf_stub.gerar_comprovante_pdf = lambda *a, **k: ''
pdf_stub.gerar_certificados_pdf = lambda *a, **k: ''
pdf_stub.gerar_certificado_personalizado = lambda *a, **k: ''
pdf_stub.gerar_pdf_comprovante_agendamento = lambda *a, **k: ''
pdf_stub.gerar_pdf_inscritos_pdf = lambda *a, **k: ''
pdf_stub.gerar_lista_frequencia_pdf = lambda *a, **k: ''
pdf_stub.gerar_pdf_feedback = lambda *a, **k: ''
pdf_stub.gerar_etiquetas = lambda *a, **k: None
pdf_stub.gerar_lista_frequencia = lambda *a, **k: None
pdf_stub.gerar_certificados = lambda *a, **k: None
pdf_stub.gerar_evento_qrcode_pdf = lambda *a, **k: None
pdf_stub.gerar_qrcode_token = lambda *a, **k: None
pdf_stub.gerar_programacao_evento_pdf = lambda *a, **k: None
pdf_stub.gerar_placas_oficinas_pdf = lambda *a, **k: None
pdf_stub.exportar_checkins_pdf_opcoes = lambda *a, **k: None
pdf_stub.gerar_revisor_details_pdf = lambda *a, **k: None
pdf_stub.gerar_pdf_relatorio_agendamentos = lambda *a, **k: None
sys.modules.setdefault('services.pdf_service', pdf_stub)

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from flask import Flask
from flask import render_template
from extensions import db, login_manager
from flask_migrate import upgrade

from datetime import datetime, timedelta

    Cliente,
    Formulario,
    CampoFormulario,
    RevisorProcess,
    RevisorCandidatura,
    Usuario,
    Submission,
    Assignment,
    Evento,
)
from app import create_app
import routes.dashboard_cliente  # noqa: F401


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_ENGINE_OPTIONS=Config.build_engine_options("sqlite://"),
        SECRET_KEY="test",
    )
    templates_path = os.path.join(os.path.dirname(__file__), "..", "templates")
    app.template_folder = templates_path


    with app.app_context():
        try:
            upgrade(revision="heads")
        except SystemExit:
            db.create_all()
        cliente = Cliente(
            nome="Cli", email="cli@test", senha=generate_password_hash("123")
        )
        db.session.add(cliente)
        db.session.commit()
        form = Formulario(nome="Cand", cliente_id=cliente.id)
        db.session.add(form)
        db.session.commit()
        event = Evento(
            cliente_id=cliente.id,
            nome="E1",
            inscricao_gratuita=True,
            publico=True,
        )
        db.session.add(event)
        db.session.commit()
        form.eventos.append(event)
        db.session.commit()
        campo_email = CampoFormulario(formulario_id=form.id, nome="email", tipo="text")
        campo_nome = CampoFormulario(formulario_id=form.id, nome="nome", tipo="text")
        db.session.add_all([campo_email, campo_nome])
        db.session.commit()
        evento = Evento(
            cliente_id=cliente.id,
            nome="E1",
            inscricao_gratuita=True,
            publico=True,
        )
        db.session.add(evento)
        db.session.commit()
        now = datetime.utcnow()
        proc = RevisorProcess(
            cliente_id=cliente.id,
            formulario_id=form.id,
            num_etapas=1,
            availability_start=now - timedelta(days=1),
            availability_end=now + timedelta(days=1),
            exibir_para_participantes=True,
        )
        proc.eventos.append(evento)
        db.session.add(proc)
        db.session.commit()
        sub = Submission(title="T", locator="loc", code_hash="x")
        db.session.add(sub)
        participante = Usuario(
            nome="Part",
            cpf="3",
            email="part@test",
            senha=generate_password_hash("123"),
            formacao="x",
            tipo="participante",
        )
        db.session.add(participante)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post(
        "/login", data={"email": email, "senha": senha}, follow_redirects=False
    )


def test_application_and_approval_flow(client, app):
    with app.app_context():
        proc = RevisorProcess.query.first()
        campos = {c.nome: c.id for c in proc.formulario.campos}
        sub = Submission.query.first()

    resp = client.post(
        f"/revisor/apply/{proc.id}",
        data={str(campos["email"]): "rev@test", str(campos["nome"]): "Rev"},
    )
    assert resp.status_code in (302, 200)

    with app.app_context():
        cand = RevisorCandidatura.query.first()
        assert cand.email == "rev@test"
        cand_id = cand.id
        code = cand.codigo

    resp = client.get(f"/revisor/progress/{code}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert code in html
    assert "Baixar PDF" in html
    assert f"/revisor/progress/{code}/pdf" in html

    login(client, "cli@test", "123")
    resp = client.post(f"/revisor/approve/{cand_id}", json={})
    assert resp.status_code == 200
    assert resp.get_json()["success"]

    with app.app_context():
        cand = RevisorCandidatura.query.get(cand_id)
        assert cand.status == "aprovado"
        user = Usuario.query.filter_by(email="rev@test").first()
        assert user and user.tipo == "revisor"
        ass = Assignment.query.filter_by(reviewer_id=user.id).first()
        assert ass is None


def test_progress_pdf_download(client, app):
    with app.app_context():
        proc = RevisorProcess.query.first()
        campos = {c.nome: c.id for c in proc.formulario.campos}

    client.post(
        f"/revisor/apply/{proc.id}",
        data={str(campos["email"]): "pdf@test", str(campos["nome"]): "Pdf"},
    )

    with app.app_context():
        cand = RevisorCandidatura.query.filter_by(email="pdf@test").first()
        code = cand.codigo

    resp = client.get(f"/revisor/progress/{code}/pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"


def test_navbar_shows_correct_process_id(app):
    with app.test_request_context("/"):
        html = render_template("partials/navbar.html")
    assert "/processo_seletivo" in html


def test_navbar_without_reviewer_registration_link(app):
    with app.test_request_context("/"):
        html = render_template("partials/navbar.html")
    assert "Inscrever-se como revisor" not in html


def test_navbar_shows_link_when_unavailable(app):
    with app.app_context():
        proc = RevisorProcess.query.first()
        # torna o processo indisponivel
        proc.availability_start = datetime.utcnow() - timedelta(days=2)
        proc.availability_end = datetime.utcnow() - timedelta(days=1)
        db.session.commit()
        with app.test_request_context("/"):
            html = render_template("partials/navbar.html")
        assert "/processo_seletivo" in html


def test_navbar_shows_link_for_participant_when_disabled(client, app):
    with app.app_context():
        proc = RevisorProcess.query.first()
        proc.exibir_para_participantes = False
        participante = Usuario.query.filter_by(email="part@test").first()
        db.session.commit()
        from flask_login import login_user, logout_user

        with app.test_request_context("/"):
            login_user(participante)
            html = render_template("partials/navbar.html")
            logout_user()
        assert "/processo_seletivo" in html


def test_is_available_method():
    now = datetime.utcnow()
    proc = RevisorProcess(
        availability_start=now - timedelta(hours=1),
        availability_end=now + timedelta(hours=1),
    )
    assert proc.is_available()

    proc.availability_end = now - timedelta(minutes=1)
    assert not proc.is_available()


def test_dashboard_lists_candidaturas_and_status_update(client, app):
    with app.app_context():
        proc = RevisorProcess.query.first()
        campos = {c.nome: c.id for c in proc.formulario.campos}

    client.post(
        f"/revisor/apply/{proc.id}",
        data={str(campos["email"]): "cand@test", str(campos["nome"]): "Cand"},
    )

    with app.app_context():
        cand = RevisorCandidatura.query.filter_by(email="cand@test").first()
        assert cand is not None
        cand_id = cand.id
        cand_code = cand.codigo

    login(client, "cli@test", "123")
    resp = client.get("/dashboard_cliente")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Cand" in html
    assert cand_code in html

    resp = client.post(f"/revisor/reject/{cand_id}", json={})
    assert resp.status_code == 200
    assert resp.get_json()["success"]

    with app.app_context():
        cand = RevisorCandidatura.query.get(cand_id)
        assert cand.status == "rejeitado"


def test_approve_candidatura_without_email(client, app):
    """Approving a candidatura without email should still succeed."""
    with app.app_context():
        proc = RevisorProcess.query.first()
        campos = {c.nome: c.id for c in proc.formulario.campos}

    # submit candidatura only with nome
    client.post(
        f"/revisor/apply/{proc.id}",
        data={str(campos["nome"]): "SemEmail"},
    )

    with app.app_context():
        cand = RevisorCandidatura.query.filter_by(nome="SemEmail").first()
        assert cand.email is None
        cand_id = cand.id

    login(client, "cli@test", "123")
    resp = client.post(f"/revisor/approve/{cand_id}", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"]
    assert "reviewer_id" not in data
    with app.app_context():
        cand = RevisorCandidatura.query.get(cand_id)
        assert cand.status == "aprovado"


def test_missing_required_field(client, app):
    with app.app_context():
        proc = RevisorProcess.query.first()
        campos = {c.nome: c.id for c in proc.formulario.campos}
        campo_nome = CampoFormulario.query.get(campos["nome"])
        campo_nome.obrigatorio = True
        db.session.commit()
        proc_id = proc.id
        email_id = campos["email"]
        base = RevisorCandidatura.query.count()

    resp = client.post(
        f"/revisor/apply/{proc_id}",
        data={str(email_id): "req@test"},
        follow_redirects=True,
    )
    assert "O campo nome é obrigatório.".encode() in resp.data

    with app.app_context():
        assert RevisorCandidatura.query.count() == base


def test_duplicate_email(client, app):
    with app.app_context():
        proc = RevisorProcess.query.first()
        campos = {c.nome: c.id for c in proc.formulario.campos}
        proc_id = proc.id
        email_id = campos["email"]
        nome_id = campos["nome"]
        start = RevisorCandidatura.query.count()

    client.post(
        f"/revisor/apply/{proc_id}",
        data={str(email_id): "dup@test", str(nome_id): "A"},
    )

    with app.app_context():
        first_count = RevisorCandidatura.query.count()
        assert first_count == start + 1

    resp = client.post(
        f"/revisor/apply/{proc_id}",
        data={str(email_id): "dup@test", str(nome_id): "B"},
        follow_redirects=True,
    )
    assert (
        "Já existe uma candidatura com este e-mail para este processo.".encode()
        in resp.data
    )

    with app.app_context():
        assert RevisorCandidatura.query.count() == first_count
