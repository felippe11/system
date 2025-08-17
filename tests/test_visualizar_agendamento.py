import os
import pytest
from werkzeug.security import generate_password_hash

# Import stubs from existing test to satisfy optional dependencies
import sys
import types

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

sys.modules.setdefault('pandas', types.ModuleType('pandas'))
sys.modules.setdefault('qrcode', types.ModuleType('qrcode'))
sys.modules.setdefault('openpyxl', types.ModuleType('openpyxl'))
sys.modules['openpyxl'].Workbook = object

pil_stub = types.ModuleType('PIL')
pil_stub.Image = types.SimpleNamespace(new=lambda *a, **k: None, open=lambda *a, **k: None)
pil_stub.ImageDraw = types.SimpleNamespace(Draw=lambda *a, **k: None)
pil_stub.ImageFont = types.SimpleNamespace(truetype=lambda *a, **k: None)
sys.modules.setdefault('PIL', pil_stub)

sys.modules.setdefault('requests', types.ModuleType('requests'))
sys.modules.setdefault('reportlab', types.ModuleType('reportlab'))
sys.modules.setdefault('reportlab.lib', types.ModuleType('reportlab.lib'))
sys.modules.setdefault('reportlab.lib.pagesizes', types.ModuleType('reportlab.lib.pagesizes'))
sys.modules['reportlab.lib.pagesizes'].letter = None
sys.modules['reportlab.lib.pagesizes'].landscape = None
sys.modules['reportlab.lib.pagesizes'].A4 = None
sys.modules.setdefault('reportlab.lib.units', types.ModuleType('reportlab.lib.units'))
sys.modules['reportlab.lib.units'].inch = None
sys.modules['reportlab.lib.units'].mm = None
sys.modules.setdefault('reportlab.pdfgen', types.ModuleType('reportlab.pdfgen'))
sys.modules.setdefault('reportlab.pdfgen.canvas', types.ModuleType('reportlab.pdfgen.canvas'))
sys.modules.setdefault('reportlab.lib.colors', types.ModuleType('reportlab.lib.colors'))
sys.modules.setdefault('reportlab.platypus', types.ModuleType('reportlab.platypus'))
reportlab_platypus = sys.modules['reportlab.platypus']
reportlab_platypus.SimpleDocTemplate = object
reportlab_platypus.Table = object
reportlab_platypus.TableStyle = object
reportlab_platypus.Paragraph = object
reportlab_platypus.Spacer = object
sys.modules.setdefault('reportlab.lib.styles', types.ModuleType('reportlab.lib.styles'))
sys.modules['reportlab.lib.styles'].getSampleStyleSheet = lambda: None

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
os.environ.setdefault('SECRET_KEY', 'test')

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models.user import Usuario


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        admin = Usuario(
            nome='Admin',
            cpf='1',
            email='admin@test',
            senha=generate_password_hash('123'),
            formacao='x',
            tipo='admin'
        )
        db.session.add(admin)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post('/login', data={'email': 'admin@test', 'senha': '123'}, follow_redirects=True)


def test_visualizar_agendamento_not_found(client):
    login(client)
    resp = client.get('/visualizar/999', headers={'Accept': 'application/json'})
    assert resp.status_code == 404
    assert resp.is_json
    assert resp.get_json() == {'erro': 'Agendamento não encontrado'}

