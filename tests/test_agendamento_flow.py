import os
import sys
import types
from datetime import date, time

import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
os.environ.setdefault('SECRET_KEY', 'test')

from config import Config

# --- Stubs de módulos externos ---
utils_stub = types.ModuleType('utils')
taxa_service = types.ModuleType('utils.taxa_service')
taxa_service.calcular_taxa_cliente = lambda *a, **k: {
    'taxa_aplicada': 0,
    'usando_taxa_diferenciada': False
}
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

utils_security = types.ModuleType('utils.security')
utils_security.sanitize_input = lambda x: x
utils_security.password_is_strong = lambda x: True
sys.modules.setdefault('utils.security', utils_security)

utils_mfa = types.ModuleType('utils.mfa')
utils_mfa.mfa_required = lambda f: f
sys.modules.setdefault('utils.mfa', utils_mfa)

pdf_service_stub = types.ModuleType('services.pdf_service')


def dummy_pdf(*args, **kwargs):
    path = args[-1] if len(args) >= 6 else kwargs.get('pdf_path', 'dummy.pdf')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'PDF')
    return path


pdf_service_stub.gerar_pdf_comprovante_agendamento = dummy_pdf
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

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import (
    Cliente,
    Usuario,
    Evento,
    ConfiguracaoCliente,
    HorarioVisitacao,
    AgendamentoVisita,
    AlunoVisitante,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()

        db.session.add(ConfiguracaoCliente(cliente_id=cliente.id, permitir_checkin_global=True))
        db.session.commit()

        evento = Evento(cliente_id=cliente.id, nome='Evento', habilitar_lotes=False, inscricao_gratuita=True)
        db.session.add(evento)
        db.session.commit()

        horario = HorarioVisitacao(evento_id=evento.id, data=date.today(), horario_inicio=time(9, 0),
                                   horario_fim=time(10, 0), capacidade_total=30, vagas_disponiveis=30)
        db.session.add(horario)

        professor = Usuario(nome='Prof', cpf='222', email='prof@test',
                            senha=generate_password_hash('p123'), formacao='F', tipo='professor')
        db.session.add(professor)
        db.session.commit()

    return app


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=False)


def test_fluxo_agendamento(app):
    client = app.test_client()

    login(client, 'prof@test', 'p123')

    with app.app_context():
        evento = Evento.query.first()
        horario = HorarioVisitacao.query.first()

    resp = client.post('/criar-agendamento', data={
        'evento_id': evento.id,
        'data': str(horario.data),
        'horario_id': horario.id,
        'escola_nome': 'Escola X',
        'nome_responsavel': 'Resp',
        'email_responsavel': 'resp@test',
        'telefone_escola': '123',
        'turma': 'T1',
        'quantidade_alunos': 5,
        'faixa_etaria': 'Fundamental',
        'observacoes': ''
    }, follow_redirects=False)

    assert resp.status_code == 302
    assert '/professor/adicionar_alunos/' in resp.headers['Location']
    agendamento_id = int(resp.headers['Location'].rstrip('/').split('/')[-1])

    resp = client.post(f'/professor/adicionar_alunos/{agendamento_id}',
                       data={'nome': 'Aluno 1', 'cpf': '12345678901'},
                       follow_redirects=False)
    assert resp.status_code == 302

    resp = client.get(f'/professor/imprimir_agendamento/{agendamento_id}')
    assert resp.status_code == 200
    assert resp.data.startswith(b'PDF')
