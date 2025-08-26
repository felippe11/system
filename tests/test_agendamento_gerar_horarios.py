import os
import sys
import types
from datetime import date, timedelta, time

import pytest
from werkzeug.security import generate_password_hash

# Stubs for external dependencies used by agendamento routes
utils_stub = types.ModuleType('utils')
taxa_service = types.ModuleType('utils.taxa_service')


def _taxa_dummy(*args, **kwargs):
    return {'taxa_aplicada': 0, 'usando_taxa_diferenciada': False}


taxa_service.calcular_taxa_cliente = _taxa_dummy
taxa_service.calcular_taxas_clientes = lambda *a, **k: []
utils_stub.taxa_service = taxa_service
utils_stub.preco_com_taxa = lambda *a, **k: 1
utils_stub.obter_estados = lambda *a, **k: []
utils_stub.external_url = lambda *a, **k: ''
utils_stub.gerar_comprovante_pdf = lambda *a, **k: ''
utils_stub.enviar_email = lambda *a, **k: None
utils_stub.formatar_brasilia = lambda *a, **k: ''
utils_stub.determinar_turno = lambda *a, **k: ''

sys.modules.setdefault('utils', utils_stub)
sys.modules.setdefault('utils.taxa_service', taxa_service)

dia_semana_mod = types.ModuleType('utils.dia_semana')
dia_semana_mod.dia_semana = lambda *a, **k: ''
sys.modules.setdefault('utils.dia_semana', dia_semana_mod)
utils_stub.dia_semana = dia_semana_mod

utils_security = types.ModuleType('utils.security')
utils_security.sanitize_input = lambda x: x
utils_security.password_is_strong = lambda x: True
sys.modules.setdefault('utils.security', utils_security)

utils_mfa = types.ModuleType('utils.mfa')
utils_mfa.mfa_required = lambda f: f
sys.modules.setdefault('utils.mfa', utils_mfa)
utils_auth = types.ModuleType('utils.auth')
utils_auth.login_required = lambda f: f
utils_auth.require_permission = lambda *a, **k: lambda f: f
utils_auth.require_resource_access = lambda *a, **k: lambda f: f
utils_auth.role_required = lambda *a, **k: lambda f: f
utils_auth.cliente_required = lambda f: f
utils_auth.admin_required = lambda f: f
sys.modules.setdefault('utils.auth', utils_auth)
utils_revisor_helpers = types.ModuleType('utils.revisor_helpers')
utils_revisor_helpers.parse_revisor_form = lambda *a, **k: None
utils_revisor_helpers.recreate_stages = lambda *a, **k: None
utils_revisor_helpers.update_process_eventos = lambda *a, **k: None
utils_revisor_helpers.update_revisor_process = lambda *a, **k: None
sys.modules.setdefault('utils.revisor_helpers', utils_revisor_helpers)
utils_stub.revisor_helpers = utils_revisor_helpers
template_context_stub = types.ModuleType('utils.template_context')
template_context_stub.register_template_context = lambda *a, **k: None
sys.modules.setdefault('utils.template_context', template_context_stub)

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

sys.modules.setdefault('services.pdf_service', pdf_service_stub)

arquivo_utils_stub = types.ModuleType('utils.arquivo_utils')
arquivo_utils_stub.arquivo_permitido = lambda *a, **k: True
sys.modules.setdefault('utils.arquivo_utils', arquivo_utils_stub)

# Optional third-party libraries
sys.modules.setdefault('pandas', types.ModuleType('pandas'))
sys.modules.setdefault('qrcode', types.ModuleType('qrcode'))

openpyxl_stub = types.ModuleType('openpyxl')
openpyxl_stub.Workbook = object
sys.modules.setdefault('openpyxl', openpyxl_stub)

pil_stub = types.ModuleType('PIL')
pil_stub.Image = types.SimpleNamespace(
    new=lambda *a, **k: None,
    open=lambda *a, **k: None,
)
pil_stub.ImageDraw = types.SimpleNamespace(Draw=lambda *a, **k: None)
pil_stub.ImageFont = types.SimpleNamespace(truetype=lambda *a, **k: None)
sys.modules.setdefault('PIL', pil_stub)

sys.modules.setdefault('requests', types.ModuleType('requests'))

reportlab_stub = types.ModuleType('reportlab')
sys.modules.setdefault('reportlab', reportlab_stub)
reportlab_lib_stub = types.ModuleType('reportlab.lib')
sys.modules.setdefault('reportlab.lib', reportlab_lib_stub)
pagesizes_stub = types.ModuleType('reportlab.lib.pagesizes')
pagesizes_stub.letter = None
pagesizes_stub.landscape = None
pagesizes_stub.A4 = None
sys.modules.setdefault('reportlab.lib.pagesizes', pagesizes_stub)
units_stub = types.ModuleType('reportlab.lib.units')
units_stub.inch = None
units_stub.mm = None
sys.modules.setdefault('reportlab.lib.units', units_stub)
reportlab_pdfgen_stub = types.ModuleType('reportlab.pdfgen')
sys.modules.setdefault('reportlab.pdfgen', reportlab_pdfgen_stub)
sys.modules.setdefault(
    'reportlab.pdfgen.canvas', types.ModuleType('reportlab.pdfgen.canvas')
)
reportlab_colors_stub = types.ModuleType('reportlab.lib.colors')
sys.modules.setdefault('reportlab.lib.colors', reportlab_colors_stub)
platypus_stub = types.ModuleType('reportlab.platypus')
platypus_stub.SimpleDocTemplate = object
platypus_stub.Table = object
platypus_stub.TableStyle = object
platypus_stub.Paragraph = object
platypus_stub.Spacer = object
sys.modules.setdefault('reportlab.platypus', platypus_stub)
styles_stub = types.ModuleType('reportlab.lib.styles')
styles_stub.getSampleStyleSheet = lambda: None
sys.modules.setdefault('reportlab.lib.styles', styles_stub)

mailjet_rest_stub = types.ModuleType('mailjet_rest')
mailjet_client_stub = types.ModuleType('mailjet_rest.client')
class ApiError(Exception):
    pass
mailjet_client_stub.ApiError = ApiError
class Client:
    def __init__(self, *a, **k):
        pass

mailjet_rest_stub.Client = Client
mailjet_rest_stub.client = mailjet_client_stub
sys.modules.setdefault('mailjet_rest', mailjet_rest_stub)
sys.modules.setdefault('mailjet_rest.client', mailjet_client_stub)

weasyprint_stub = types.ModuleType('weasyprint')
weasyprint_stub.HTML = lambda *a, **k: None
weasyprint_stub.CSS = lambda *a, **k: None
sys.modules.setdefault('weasyprint', weasyprint_stub)

fpdf_stub = types.ModuleType('fpdf')
fpdf_stub.FPDF = object
sys.modules.setdefault('fpdf', fpdf_stub)

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('DB_PASS', 'test')

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import Cliente, Evento, ConfiguracaoAgendamento, HorarioVisitacao


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome='Cli',
            email='cli@test',
            senha=generate_password_hash('123', method='pbkdf2:sha256')
        )
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(
            cliente_id=cliente.id,
            nome='Evento',
            habilitar_lotes=False,
            inscricao_gratuita=True,
        )
        db.session.add(evento)
        db.session.commit()
        config = ConfiguracaoAgendamento(
            cliente_id=cliente.id,
            evento_id=evento.id,
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            dias_semana='0,1,2,3,4,5,6',
            intervalo_minutos=60,
            capacidade_padrao=30,
        )
        db.session.add(config)
        db.session.commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        '/login',
        data={'email': 'cli@test', 'senha': '123'},
        follow_redirects=False,
    )


def test_gera_horarios_para_todos_os_dias(app, client):
    with app.app_context():
        evento = Evento.query.first()
    login(client)
    inicio = date(2023, 9, 24)  # Domingo
    fim = inicio + timedelta(days=6)
    resp = client.post(
        f'/gerar_horarios_agendamento/{evento.id}',
        data={
            'data_inicial': inicio.strftime('%Y-%m-%d'),
            'data_final': fim.strftime('%Y-%m-%d'),
        },
        follow_redirects=True,
    )
    assert resp.status_code in (200, 302)
    with app.app_context():
        horarios = HorarioVisitacao.query.filter_by(evento_id=evento.id).all()
        assert len(horarios) == 7
        datas = {h.data for h in horarios}
        esperadas = {inicio + timedelta(days=i) for i in range(7)}
        assert datas == esperadas
