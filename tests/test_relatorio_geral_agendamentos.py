Aqui está o arquivo resolvido (sem marcadores de conflito) unificando os dois lados e mantendo os stubs, os dois testes e o setup completo do banco:

```python
import os
import sys
import types
from datetime import date, time

import pytest
from werkzeug.security import generate_password_hash
from flask import template_rendered

# --- Stubs de módulos externos (evitam dependências reais nos testes) ---
utils_stub = types.ModuleType('utils')
taxa_service = types.ModuleModuleType('utils.taxa_service') if hasattr(types, 'ModuleModuleType') else types.ModuleType('utils.taxa_service')
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

# Variáveis de ambiente mínimas para create_app
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
os.environ.setdefault('SECRET_KEY', 'test')

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Usuario, Cliente, Evento, HorarioVisitacao, AgendamentoVisita


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'

    with app.app_context():
        # Garante banco limpo
        db.drop_all()
        db.create_all()

        # Cliente e usuário (para login)
        cliente = Cliente(
            nome='Cli',
            email='cli@test',
            senha=generate_password_hash('123'),
        )
        db.session.add(cliente)
        db.session.flush()  # precisamos do cliente.id

        usuario = Usuario(
            id=cliente.id,  # mantém o vínculo 1-1 se o app espera isso
            nome='CliUser',
            cpf='1',
            email='cli@test',
            senha=generate_password_hash('123'),
            formacao='x',
            tipo='cliente'
        )
        db.session.add(usuario)
        db.session.commit()

        # Eventos
        evento1 = Evento(
            cliente_id=cliente.id,
            nome='Evento1',
            habilitar_lotes=False,
            inscricao_gratuita=True,
        )
        evento2 = Evento(
            cliente_id=cliente.id,
            nome='Evento2',
            habilitar_lotes=False,
            inscricao_gratuita=True,
        )
        db.session.add_all([evento1, evento2])
        db.session.flush()

        # Horários (datas distintas para testar filtro por período)
        h1 = HorarioVisitacao(
            evento_id=evento1.id,
            data=date(2024, 1, 10),
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
        )
        h2 = HorarioVisitacao(
            evento_id=evento2.id,
            data=date(2024, 2, 10),
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
        )
        db.session.add_all([h1, h2])
        db.session.flush()

        # Agendamentos associados ao evento1/h1 para alimentar 'estatisticas'
        ag1 = AgendamentoVisita(
            horario_id=h1.id,
            professor_id=None,
            escola_nome='Esc1',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=10,
            status='confirmado',
        )
        ag2 = AgendamentoVisita(
            horario_id=h1.id,
            professor_id=None,
            escola_nome='Esc2',
            turma='T2',
            nivel_ensino='Fundamental',
            quantidade_alunos=15,
            status='realizado',
        )
        ag3 = AgendamentoVisita(
            horario_id=h1.id,
            professor_id=None,
            escola_nome='Esc3',
            turma='T3',
            nivel_ensino='Fundamental',
            quantidade_alunos=5,
            status='cancelado',
        )
        db.session.add_all([ag1, ag2, ag3])
        db.session.commit()

    yield app

    # Teardown
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email='cli@test', senha='123'):
    return client.post('/login', data={'email': email, 'senha': senha})


def test_relatorio_geral_agendamentos(app, client):
    login(client)
    captured = []

    def capture(sender, template, context, **extra):
        captured.append(context)

    with template_rendered.connected_to(capture, app):
        resp = client.get('/relatorio_geral_agendamentos')

    assert resp.status_code == 200
    assert captured, "Nenhum contexto de template capturado"

    context = captured[0]
    assert 'estatisticas' in context, "Contexto não contém 'estatisticas'"
    estatisticas = context['estatisticas']

    with app.app_context():
        evento1 = Evento.query.filter_by(nome='Evento1').first()
        evento2 = Evento.query.filter_by(nome='Evento2').first()

    # Evento1 tem 3 agendamentos: confirmado(10), realizado(15), cancelado(5)
    assert estatisticas[evento1.id]['confirmados'] == 1
    assert estatisticas[evento1.id]['realizados'] == 1
    assert estatisticas[evento1.id]['cancelados'] == 1
    assert estatisticas[evento1.id]['visitantes'] == 25
    assert estatisticas[evento1.id]['total'] == 3

    # Evento2 sem agendamentos
    assert estatisticas[evento2.id]['confirmados'] == 0
    assert estatisticas[evento2.id]['realizados'] == 0
    assert estatisticas[evento2.id]['cancelados'] == 0
    assert estatisticas[evento2.id]['visitantes'] == 0
    assert estatisticas[evento2.id]['total'] == 0


def test_relatorio_geral_agendamentos_filters_by_date(client):
    login(client)
    resp = client.get('/relatorio_geral_agendamentos?data_inicio=2024-01-01&data_fim=2024-01-31')
    assert resp.status_code == 200
    # Em jan/2024 só existe Evento1
    assert b'Evento1' in resp.data
    assert b'Evento2' not in resp.data
```

Se quiser, eu também preparo um patch (`git apply`) com esse conteúdo.
