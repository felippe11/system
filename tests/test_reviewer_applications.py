import sys
import types
import uuid
import logging
import pytest
from io import BytesIO
from flask import send_file
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

# Stubs to avoid optional deps
mercadopago_stub = types.ModuleType('mercadopago')
mercadopago_stub.SDK = lambda *a, **k: None
sys.modules.setdefault('mercadopago', mercadopago_stub)
utils_stub = types.ModuleType('utils')
taxa_service = types.ModuleType('utils.taxa_service')
taxa_service.calcular_taxa_cliente = lambda *a, **k: {'taxa_aplicada': 0, 'usando_taxa_diferenciada': False}
taxa_service.calcular_taxas_clientes = lambda *a, **k: []
utils_stub.taxa_service = taxa_service
utils_stub.preco_com_taxa = lambda *a, **k: 1
utils_stub.obter_estados = lambda *a, **k: []
utils_stub.external_url = lambda *a, **k: ''
utils_stub.gerar_comprovante_pdf = lambda *a, **k: ''
utils_stub.enviar_email = lambda *a, **k: None
utils_stub.formatar_brasilia = lambda *a, **k: ''
utils_stub.determinar_turno = lambda *a, **k: ''
utils_stub.endpoints = types.SimpleNamespace(DASHBOARD='dashboard')
sys.modules.setdefault('utils', utils_stub)
utils_security = types.ModuleType('utils.security')
utils_security.sanitize_input = lambda x: x
utils_security.password_is_strong = lambda x: True
sys.modules.setdefault('utils.security', utils_security)
utils_mfa = types.ModuleType('utils.mfa')
utils_mfa.mfa_required = lambda f: f
sys.modules.setdefault('utils.mfa', utils_mfa)
sys.modules.setdefault('utils.taxa_service', taxa_service)
utils_dia_semana = types.ModuleType('utils.dia_semana')
utils_dia_semana.dia_semana = lambda *a, **k: ''
sys.modules.setdefault('utils.dia_semana', utils_dia_semana)
utils_revisor_helpers = types.ModuleType('utils.revisor_helpers')
utils_revisor_helpers.parse_revisor_form = lambda *a, **k: {}
utils_revisor_helpers.update_revisor_process = lambda *a, **k: None
utils_revisor_helpers.update_process_eventos = lambda *a, **k: None
utils_revisor_helpers.recreate_stages = lambda *a, **k: None
sys.modules.setdefault('utils.revisor_helpers', utils_revisor_helpers)
pdf_service_stub = types.ModuleType('services.pdf_service')
pdf_service_stub.gerar_pdf_respostas = lambda *a, **k: None
pdf_service_stub.gerar_comprovante_pdf = lambda *a, **k: ''
pdf_service_stub.gerar_certificados_pdf = lambda *a, **k: ''
pdf_service_stub.gerar_certificado_personalizado = lambda *a, **k: ''
pdf_service_stub.gerar_pdf_comprovante_agendamento = lambda *a, **k: ''
pdf_service_stub.gerar_pdf_inscritos_pdf = lambda *a, **k: ''
pdf_service_stub.gerar_lista_frequencia_pdf = lambda *a, **k: ''
pdf_service_stub.gerar_pdf_feedback = lambda *a, **k: ''
pdf_service_stub.gerar_etiquetas = lambda *a, **k: send_file(BytesIO(b''), download_name='x.pdf')
pdf_service_stub.gerar_lista_frequencia = lambda *a, **k: send_file(BytesIO(b''), download_name='x.pdf')
pdf_service_stub.gerar_certificados = lambda *a, **k: send_file(BytesIO(b''), download_name='x.pdf')
pdf_service_stub.gerar_evento_qrcode_pdf = lambda *a, **k: send_file(BytesIO(b''), download_name='x.pdf')
pdf_service_stub.gerar_qrcode_token = lambda *a, **k: send_file(BytesIO(b''), download_name='x.png')
pdf_service_stub.gerar_programacao_evento_pdf = lambda *a, **k: send_file(BytesIO(b''), download_name='x.pdf')
pdf_service_stub.gerar_placas_oficinas_pdf = lambda *a, **k: send_file(BytesIO(b''), download_name='x.pdf')
pdf_service_stub.exportar_checkins_pdf_opcoes = lambda *a, **k: send_file(BytesIO(b''), download_name='x.pdf')
pdf_service_stub.gerar_revisor_details_pdf = lambda *a, **k: send_file(BytesIO(b''), download_name='x.pdf')
sys.modules.setdefault('services.pdf_service', pdf_service_stub)
arquivo_utils_stub = types.ModuleType('utils.arquivo_utils')
arquivo_utils_stub.arquivo_permitido = lambda *a, **k: True
sys.modules.setdefault('utils.arquivo_utils', arquivo_utils_stub)

from app import create_app
from extensions import db, login_manager

from models import (
    Usuario,
    Cliente,
    ReviewerApplication,
    Formulario,
    CampoFormulario,
    RevisorProcess,
    RevisorCandidatura,
    Evento,
)
from routes.auth_routes import auth_routes

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123', method="pbkdf2:sha256"))
        admin = Usuario(nome='Admin', cpf='1', email='admin@test', senha=generate_password_hash('123', method="pbkdf2:sha256"), formacao='x', tipo='admin')
        user = Usuario(nome='User', cpf='2', email='user@test', senha=generate_password_hash('123', method="pbkdf2:sha256"), formacao='x')
        db.session.add_all([cliente, admin, user])
        db.session.commit()
        db.session.add(ReviewerApplication(usuario_id=user.id))
        db.session.commit()
        def gerar_etiquetas_route(cliente_id):
            return ''

        if 'routes.gerar_etiquetas_route' not in app.view_functions:
            app.add_url_rule(
                '/gerar_etiquetas/<int:cliente_id>',
                endpoint='routes.gerar_etiquetas_route',
                view_func=gerar_etiquetas_route,
            )
        def gerar_placas_oficinas(evento_id):
            return ''

        if 'routes.gerar_placas_oficinas' not in app.view_functions:
            app.add_url_rule(
                '/gerar_placas_oficinas/<int:evento_id>',
                endpoint='routes.gerar_placas_oficinas',
                view_func=gerar_placas_oficinas,
            )
        def exportar_checkins_filtrados():
            return ''

        if 'routes.exportar_checkins_filtrados' not in app.view_functions:
            app.add_url_rule(
                '/exportar_checkins_filtrados',
                endpoint='routes.exportar_checkins_filtrados',
                view_func=exportar_checkins_filtrados,
            )
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_dashboard_applications_visible_for_cliente(client, app):
    login(client, 'cli@test', '123')
    resp = client.get('/dashboard_cliente')
    assert resp.status_code == 200
    assert 'processo seletivo de revisores'.encode() in resp.data.lower()


def test_update_application_requires_permission(client, app):
    with app.app_context():
        rid = ReviewerApplication.query.first().id

    login(client, 'user@test', '123')
    resp = client.post(f'/reviewer_applications/{rid}', data={'action': 'advance'}, follow_redirects=True)
    assert b'dashboard' in resp.data
    with app.app_context():
        assert ReviewerApplication.query.get(rid).stage == 'novo'

    login(client, 'cli@test', '123')
    resp = client.post(f'/reviewer_applications/{rid}', data={'action': 'advance'}, follow_redirects=True)
    assert resp.status_code in (200, 302)
    with app.app_context():
        assert ReviewerApplication.query.get(rid).stage == 'triagem'

def test_submit_application_and_visibility(client, app):
    with app.app_context():
        new_user = Usuario(
            nome='Applicant', cpf='3', email='app@test',
            senha=generate_password_hash('123', method="pbkdf2:sha256"), formacao='x'
        )
        db.session.add(new_user)
        db.session.commit()
        uid = new_user.id
    login(client, 'app@test', '123')
    resp = client.post('/reviewer_applications/new', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Candidatura Recebida' in resp.data
    with app.app_context():
        assert ReviewerApplication.query.filter_by(usuario_id=uid).count() == 1
    login(client, 'cli@test', '123')
    resp = client.get('/dashboard_cliente')
    assert resp.status_code == 200


def test_revisor_approval_without_email(client, app):
    """Candidaturas sem email devem ser aprovadas sem criar usuario."""
    with app.app_context():
        cliente = Cliente.query.filter_by(email='cli@test').first()
        form = Formulario(nome='Form', cliente_id=cliente.id)
        db.session.add(form)
        db.session.commit()
        campo_nome = CampoFormulario(formulario_id=form.id, nome='nome', tipo='text')
        db.session.add(campo_nome)
        db.session.commit()
        proc = RevisorProcess(cliente_id=cliente.id, formulario_id=form.id, num_etapas=1)
        db.session.add(proc)
        db.session.commit()
        campo_id = campo_nome.id
        proc_id = proc.id

    client.post(f'/revisor/apply/{proc_id}', data={str(campo_id): 'NoEmail'})
    with app.app_context():
        cand = RevisorCandidatura.query.filter_by(nome='NoEmail').first()
        cand_id = cand.id

    login(client, 'cli@test', '123')
    resp = client.post(f'/revisor/approve/{cand_id}', json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success']
    assert 'reviewer_id' not in data
    with app.app_context():
        cand = RevisorCandidatura.query.get(cand_id)
        assert cand.status == 'aprovado'


def test_duplicate_application_redirects(client, app):
    login(client, 'user@test', '123')
    resp = client.post('/reviewer_applications/new', follow_redirects=True)
    assert resp.status_code == 200
    assert 'já foi registrada'.encode() in resp.data
    with app.app_context():
        user = Usuario.query.filter_by(email='user@test').first()
        assert ReviewerApplication.query.filter_by(usuario_id=user.id).count() == 1


def test_approve_revisor_cpf_collision(client, app, monkeypatch):
    """Gera novo CPF quando ocorre colisão durante aprovação."""
    with app.app_context():
        cliente = Cliente.query.filter_by(email='cli@test').first()
        form = Formulario(nome='Form', cliente_id=cliente.id)
        db.session.add(form)
        db.session.commit()
        proc = RevisorProcess(
            cliente_id=cliente.id, formulario_id=form.id, num_etapas=1
        )
        db.session.add(proc)
        db.session.commit()
        cand = RevisorCandidatura(
            process_id=proc.id, nome='Cand', email='cand@test'
        )
        db.session.add(cand)
        existing = Usuario(
            nome='Exist',
            cpf='12345678901',
            email='exist@test',
            senha=generate_password_hash('123', method="pbkdf2:sha256"),
            formacao='x',
        )
        db.session.add(existing)
        db.session.commit()
        cand_id = cand.id

        collisions = [
            uuid.UUID(int=int(existing.cpf)),
            uuid.UUID(int=99999999999),
        ]
        uuid_iter = iter(collisions)
        monkeypatch.setattr(uuid, 'uuid4', lambda: next(uuid_iter))
        import routes.revisor_routes as rr
        monkeypatch.setattr(rr.send_email_task, 'delay', lambda *a, **k: None)

    login(client, 'cli@test', '123')
    resp = client.post(f'/revisor/approve/{cand_id}', json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success']
    reviewer_id = data['reviewer_id']
    with app.app_context():
        reviewer = Usuario.query.get(reviewer_id)
        assert reviewer.cpf != '12345678901'


def test_approve_revisor_cpf_collision_error(client, app, monkeypatch, caplog):
    """Notifica operador após colisões repetidas de CPF."""
    with app.app_context():
        cliente = Cliente.query.filter_by(email='cli@test').first()
        form = Formulario(nome='Form', cliente_id=cliente.id)
        db.session.add(form)
        db.session.commit()
        proc = RevisorProcess(
            cliente_id=cliente.id, formulario_id=form.id, num_etapas=1
        )
        db.session.add(proc)
        db.session.commit()
        cand = RevisorCandidatura(
            process_id=proc.id, nome='Cand', email='cand2@test'
        )
        db.session.add(cand)
        existing = Usuario(
            nome='Exist',
            cpf='12345678901',
            email='exist@test',
            senha=generate_password_hash('123', method="pbkdf2:sha256"),
            formacao='x',
        )
        db.session.add(existing)
        db.session.commit()
        cand_id = cand.id

        monkeypatch.setattr(uuid, 'uuid4', lambda: uuid.UUID(int=int(existing.cpf)))
        import routes.revisor_routes as rr
        monkeypatch.setattr(rr.send_email_task, 'delay', lambda *a, **k: None)

    login(client, 'cli@test', '123')
    caplog.set_level(logging.ERROR)
    resp = client.post(f'/revisor/approve/{cand_id}', json={})
    assert resp.status_code == 500
    data = resp.get_json()
    assert not data['success']
    assert 'CPF' in data['error']
    assert 'Falha ao gerar CPF' in caplog.text
    with app.app_context():
        cand_db = RevisorCandidatura.query.get(cand_id)
        assert cand_db.status == 'pendente'
        assert Usuario.query.filter_by(email='cand2@test').first() is None


def test_eligible_events_filters_by_status(client, app):
    with app.app_context():
        cliente = Cliente.query.filter_by(email='cli@test').first()
        form = Formulario(nome='Form2', cliente_id=cliente.id)
        cliente2 = Cliente(nome='Cli2', email='cli2@test', senha=generate_password_hash('123', method="pbkdf2:sha256"))
        db.session.add_all([form, cliente2])
        db.session.commit()
        form2 = Formulario(nome='Form3', cliente_id=cliente2.id)
        db.session.add(form2)
        db.session.commit()
        e_active = Evento(
            cliente_id=cliente.id,
            nome='EA',
            inscricao_gratuita=True,
            publico=True,
            status='ativo',
        )
        e_inactive = Evento(
            cliente_id=cliente2.id,
            nome='EI',
            inscricao_gratuita=True,
            publico=True,
            status='ativo',
        )
        db.session.add_all([e_active, e_inactive])
        db.session.commit()
        proc_active = RevisorProcess(
            cliente_id=cliente.id,
            formulario_id=form.id,
            num_etapas=1,
            availability_start=datetime.utcnow() - timedelta(days=1),
            availability_end=datetime.utcnow() + timedelta(days=1),
            exibir_para_participantes=True,
            status='ativo',
            eventos=[e_active],
        )
        proc_inactive = RevisorProcess(
            cliente_id=cliente2.id,
            formulario_id=form2.id,
            num_etapas=1,
            availability_start=datetime.utcnow() - timedelta(days=1),
            availability_end=datetime.utcnow() + timedelta(days=1),
            exibir_para_participantes=True,
            status='finalizado',
            eventos=[e_inactive],
        )
        db.session.add_all([proc_active, proc_inactive])
        db.session.commit()
        e_active_id, e_inactive_id = e_active.id, e_inactive.id

    resp = client.get('/revisor/eligible_events')
    assert resp.status_code == 200
    data = resp.get_json()
    assert {'id': e_active_id, 'nome': 'EA'} in data
    assert {'id': e_inactive_id, 'nome': 'EI'} not in data
