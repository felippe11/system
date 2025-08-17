import os
import sys
import types
import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")
from config import Config

# Stubs for optional dependencies
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

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db

    Cliente,
    Formulario,
    CampoFormulario,
    RevisorProcess,
    RevisorCandidatura,
    RevisorEtapa,
    RevisorCandidaturaEtapa,
)
import tasks
import routes.revisor_routes as rr


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, SECRET_KEY='test')
    templates_path = os.path.join(os.path.dirname(__file__), '..', 'templates')
    app.template_folder = templates_path

    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome='Cli', email='cli@test', senha=generate_password_hash('123')
        )
        db.session.add(cliente)
        db.session.commit()
        form = Formulario(nome='Cand', cliente_id=cliente.id)
        db.session.add(form)
        db.session.commit()
        campo_email = CampoFormulario(
            formulario_id=form.id, nome='email', tipo='text'
        )
        campo_nome = CampoFormulario(
            formulario_id=form.id, nome='nome', tipo='text'
        )
        db.session.add_all([campo_email, campo_nome])
        db.session.commit()
        proc = RevisorProcess(
            cliente_id=cliente.id,
            formulario_id=form.id,
            num_etapas=3,
            exibir_para_participantes=True,
        )
        db.session.add(proc)
        db.session.commit()
        for i in range(1, proc.num_etapas + 1):
            db.session.add(
                RevisorEtapa(process_id=proc.id, numero=i, nome=f"Etapa {i}")
            )
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post(
        '/login', data={'email': email, 'senha': senha}, follow_redirects=False
    )


def create_candidate(app, email='cand@test'):
    with app.app_context():
        proc = RevisorProcess.query.first()
        cand = RevisorCandidatura(
            process_id=proc.id, nome='Cand', email=email
        )
        db.session.add(cand)
        db.session.commit()
        return cand.id, cand.codigo, cand.email


def patch_email(monkeypatch):
    calls = []

    def fake_delay(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(tasks.send_email_task, 'delay', fake_delay)
    monkeypatch.setattr(rr.send_email_task, 'delay', fake_delay)
    return calls


def test_approve_sends_email(client, app, monkeypatch):
    cand_id, codigo, email = create_candidate(app)
    calls = patch_email(monkeypatch)
    login(client, 'cli@test', '123')
    resp = client.post(f'/revisor/approve/{cand_id}', json={})
    assert resp.status_code == 200
    assert calls
    args, kwargs = calls[0]
    assert args[0] == email
    assert kwargs['template_path'] == 'emails/revisor_status_change.html'
    assert kwargs['template_context']['status'] == 'aprovado'
    assert kwargs['template_context']['codigo'] == codigo


def test_reject_sends_email(client, app, monkeypatch):
    cand_id, codigo, email = create_candidate(app, email='rej@test')
    calls = patch_email(monkeypatch)
    login(client, 'cli@test', '123')
    resp = client.post(f'/revisor/reject/{cand_id}', json={})
    assert resp.status_code == 200
    assert calls
    args, kwargs = calls[0]
    assert args[0] == email
    assert kwargs['template_context']['status'] == 'rejeitado'
    assert kwargs['template_context']['codigo'] == codigo


def test_advance_sends_email(client, app, monkeypatch):
    cand_id, codigo, email = create_candidate(app, email='adv@test')
    calls = patch_email(monkeypatch)
    login(client, 'cli@test', '123')
    resp = client.post(f'/revisor/advance/{cand_id}', json={})
    assert resp.status_code == 200
    assert calls
    args, kwargs = calls[0]
    assert args[0] == email
    assert kwargs['template_context']['status'] == 'pendente'
    assert kwargs['template_context']['codigo'] == codigo


def test_advance_updates_stage_status(client, app):
    cand_id, codigo, _ = create_candidate(app, email='stage@test')
    login(client, 'cli@test', '123')
    resp = client.post(f'/revisor/advance/{cand_id}', json={})
    assert resp.status_code == 200
    with app.app_context():
        cand = RevisorCandidatura.query.get(cand_id)
        etapa1 = RevisorEtapa.query.filter_by(
            process_id=cand.process_id, numero=1
        ).first()
        etapa2 = RevisorEtapa.query.filter_by(
            process_id=cand.process_id, numero=2
        ).first()
        status1 = RevisorCandidaturaEtapa.query.filter_by(
            candidatura_id=cand.id, etapa_id=etapa1.id
        ).first()
        status2 = RevisorCandidaturaEtapa.query.filter_by(
            candidatura_id=cand.id, etapa_id=etapa2.id
        ).first()
        assert status1.status == 'concluída'
        assert status2.status == 'em_andamento'
