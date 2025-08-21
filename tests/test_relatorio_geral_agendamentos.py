
import os
import sys
import types
from datetime import date, time, datetime, timedelta

import contextlib

import pytest
from flask import template_rendered
from werkzeug.security import generate_password_hash

# Stubs for optional dependencies
sys.modules.setdefault('pandas', types.ModuleType('pandas'))
sys.modules.setdefault('qrcode', types.ModuleType('qrcode'))
sys.modules.setdefault('openpyxl', types.ModuleType('openpyxl'))
sys.modules['openpyxl'].Workbook = object
sys.modules.setdefault('PIL', types.ModuleType('PIL'))
sys.modules['PIL'].Image = types.SimpleNamespace(
    new=lambda *a, **k: None, open=lambda *a, **k: None
)
sys.modules.setdefault('reportlab', types.ModuleType('reportlab'))
sys.modules.setdefault('reportlab.lib', types.ModuleType('reportlab.lib'))
sys.modules.setdefault('reportlab.lib.pagesizes',
                       types.ModuleType('reportlab.lib.pagesizes'))
rl_pages = sys.modules['reportlab.lib.pagesizes']
rl_pages.letter = None
rl_pages.landscape = None
rl_pages.A4 = None
sys.modules.setdefault('reportlab.lib.units',
                       types.ModuleType('reportlab.lib.units'))
rl_units = sys.modules['reportlab.lib.units']
rl_units.inch = None
rl_units.mm = None
sys.modules.setdefault('reportlab.pdfgen', types.ModuleType('reportlab.pdfgen'))
sys.modules.setdefault('reportlab.pdfgen.canvas',
                       types.ModuleType('reportlab.pdfgen.canvas'))
sys.modules.setdefault('reportlab.lib.colors',
                       types.ModuleType('reportlab.lib.colors'))
sys.modules.setdefault('reportlab.platypus',
                       types.ModuleType('reportlab.platypus'))
rl_plat = sys.modules['reportlab.platypus']
rl_plat.SimpleDocTemplate = object
rl_plat.Table = object
rl_plat.TableStyle = object
rl_plat.Paragraph = object
rl_plat.Spacer = object
rl_plat.Image = object
sys.modules.setdefault('fpdf', types.ModuleType('fpdf'))
sys.modules['fpdf'].FPDF = object


pdf_service_stub = types.ModuleType('services.pdf_service')
pdf_service_stub.gerar_pdf_comprovante_agendamento = lambda *a, **k: ''
pdf_service_stub.gerar_pdf_respostas = lambda *a, **k: None
pdf_service_stub.gerar_comprovante_pdf = lambda *a, **k: ''
pdf_service_stub.gerar_certificados_pdf = lambda *a, **k: ''
pdf_service_stub.gerar_certificado_personalizado = lambda *a, **k: ''
pdf_service_stub.gerar_pdf_inscritos_pdf = lambda *a, **k: ''
pdf_service_stub.gerar_lista_frequencia_pdf = lambda *a, **k: ''
pdf_service_stub.gerar_pdf_feedback = lambda *a, **k: ''
pdf_service_stub.gerar_etiquetas = lambda *a, **k: None
pdf_service_stub.gerar_lista_frequencia = lambda *a, **k: None
pdf_service_stub.gerar_certificados = lambda *a, **k: None
pdf_service_stub.gerar_evento_qrcode_pdf = lambda *a, **k: None
pdf_service_stub.gerar_qrcode_token = lambda *a, **k: None
pdf_service_stub.gerar_programacao_evento_pdf = lambda *a, **k: None
pdf_service_stub.gerar_placas_oficinas_pdf = lambda *a, **k: None
pdf_service_stub.exportar_checkins_pdf_opcoes = lambda *a, **k: None
pdf_service_stub.gerar_revisor_details_pdf = lambda *a, **k: None
pdf_service_stub.gerar_pdf_relatorio_agendamentos = lambda *a, **k: None
import services
services.pdf_service = pdf_service_stub
sys.modules.setdefault('services.pdf_service', pdf_service_stub)


os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
os.environ.setdefault('DB_PASS', 'test')

from config import Config
from app import create_app
from extensions import db
from models import (
    Evento,
    HorarioVisitacao,
    AgendamentoVisita,
    AlunoVisitante,
    Usuario,
)
from models.user import Cliente

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)



@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome='Cli', email='cli@test', senha=generate_password_hash('123')
        )
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome='EV')
        db.session.add(evento)
        db.session.commit()
        horario = HorarioVisitacao(
            evento_id=evento.id,
            data=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=100,
            vagas_disponiveis=100,
        )
        db.session.add(horario)
        db.session.commit()
        professor = Usuario(
            nome='Prof',
            cpf='00000000000',
            email='prof@test',
            senha=generate_password_hash('123'),
            formacao='x',
            tipo='professor',
        )
        db.session.add(professor)
        db.session.commit()
        ags = [
            AgendamentoVisita(
                horario_id=horario.id,
                escola_nome='E1',
                turma='T1',
                nivel_ensino='1',
                quantidade_alunos=10,
                salas_selecionadas='1',
                status='pendente',
            ),
            AgendamentoVisita(
                horario_id=horario.id,
                escola_nome='E2',
                turma='T1',
                nivel_ensino='1',
                quantidade_alunos=10,
                salas_selecionadas='1',
                status='confirmado',
                professor_id=professor.id,
                responsavel_whatsapp='55999999999',
            ),
            AgendamentoVisita(
                horario_id=horario.id,
                escola_nome='E3',
                turma='T1',
                nivel_ensino='1',
                quantidade_alunos=10,
                salas_selecionadas='1',
                status='realizado',
                checkin_realizado=True,
                data_checkin=datetime.utcnow(),
            ),
            AgendamentoVisita(
                horario_id=horario.id,
                escola_nome='E4',
                turma='T1',
                nivel_ensino='1',
                quantidade_alunos=10,
                salas_selecionadas='1',
                status='cancelado',
            ),
        ]
        db.session.add_all(ags)
        db.session.commit()
        ag_antigo = AgendamentoVisita(
            horario_id=horario.id,
            escola_nome='E5',
            turma='T1',
            nivel_ensino='1',
            quantidade_alunos=10,
            salas_selecionadas='1',
            status='pendente',
            data_agendamento=datetime.utcnow() - timedelta(days=60),
        )
        db.session.add(ag_antigo)
        db.session.commit()

        alunos = [
            AlunoVisitante(
                agendamento_id=ags[2].id,
                nome='Aluno 1',
                presente=True,
            )
        ]
        db.session.add_all(alunos)
        db.session.commit()
        app.evento_id = evento.id
    yield app



@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        '/login', data={'email': 'cli@test', 'senha': '123'}
    )


@contextlib.contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def test_counts_all_statuses(client, app):
    login(client)
    with captured_templates(app) as templates:
        resp = client.get('/relatorio_geral_agendamentos')
    assert resp.status_code == 200
    template, context = templates[0]
    stats = context['estatisticas'][app.evento_id]
    assert stats['pendentes'] == 2
    assert stats['confirmados'] == 1
    assert stats['realizados'] == 1
    assert stats['cancelados'] == 1
    assert stats['total'] == 5


def test_filter_by_horario_date_includes_old(client, app):
    login(client)
    with captured_templates(app) as templates:
        resp = client.get('/relatorio_geral_agendamentos?tipo_data=horario')
    assert resp.status_code == 200
    template, context = templates[0]
    ags = context['agendamentos']
    assert len(ags) == 5
    assert any(a.escola_nome == 'E5' for a in ags)


def test_filter_by_agendamento_date_excludes_old(client, app):
    login(client)
    with captured_templates(app) as templates:
        resp = client.get('/relatorio_geral_agendamentos?tipo_data=agendamento')
    assert resp.status_code == 200
    template, context = templates[0]
    ags = context['agendamentos']
    assert len(ags) == 4
    assert all(a.escola_nome != 'E5' for a in ags)


def test_template_contains_new_columns(client):
    login(client)
    resp = client.get('/relatorio_geral_agendamentos')
    html = resp.get_data(as_text=True)
    assert 'Check-in' in html
    assert 'Presentes' in html
    assert 'Aluno 1' in html



def test_professores_confirmados_tab(client):
    login(client)
    resp = client.get('/relatorio_geral_agendamentos')
    html = resp.get_data(as_text=True)
    assert 'Professores Confirmados' in html
    assert 'prof@test' in html
    assert 'https://api.whatsapp.com/send?phone=55999999999' in html



def test_generate_pdf_uses_service(client, monkeypatch):
    login(client)
    called = {}

    def fake_pdf(evento, agendamentos, caminho_pdf):
        called['used'] = True
        os.makedirs(os.path.dirname(caminho_pdf), exist_ok=True)
        with open(caminho_pdf, 'wb') as f:
            f.write(b'PDF')

    monkeypatch.setattr(
        'services.pdf_service.gerar_pdf_relatorio_agendamentos', fake_pdf
    )
    resp = client.get('/relatorio_geral_agendamentos?gerar_pdf=1')
    assert resp.status_code == 200

