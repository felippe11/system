import os
import sys
import types
import pytest
from werkzeug.security import generate_password_hash
from datetime import date, time
from config import Config

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')

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
pdf_service_stub.gerar_pdf_respostas = lambda *a, **k: None
pdf_service_stub.gerar_comprovante_pdf = lambda *a, **k: ''
pdf_service_stub.gerar_certificados_pdf = lambda *a, **k: ''
pdf_service_stub.gerar_certificado_personalizado = lambda *a, **k: ''
pdf_service_stub.gerar_pdf_comprovante_agendamento = lambda *a, **k: ''
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
from models import Evento, Oficina, Inscricao
from models.user import Cliente, Usuario, Ministrante
                    ConfiguracaoCliente, HorarioVisitacao, AgendamentoVisita,
                    AlunoVisitante, Checkin)

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

        db.session.add(ConfiguracaoCliente(cliente_id=cliente.id,
                                            permitir_checkin_global=True))
        db.session.commit()

        evento = Evento(cliente_id=cliente.id, nome='Evento', habilitar_lotes=False, inscricao_gratuita=True)
        db.session.add(evento)
        db.session.commit()

        ministrante = Ministrante(nome='Min', formacao='F', categorias_formacao=None,
                                  foto=None, areas_atuacao='a', cpf='mcpf', pix='1',
                                  cidade='C', estado='ST', email='min@test',
                                  senha=generate_password_hash('123'), cliente_id=cliente.id)
        db.session.add(ministrante)
        db.session.commit()

        oficina = Oficina(titulo='Oficina', descricao='Desc', ministrante_id=ministrante.id,
                          vagas=10, carga_horaria='2h', estado='ST', cidade='City',
                          cliente_id=cliente.id, evento_id=evento.id,
                          opcoes_checkin='correct,other', palavra_correta='correct')
        db.session.add(oficina)
        db.session.commit()

        participante = Usuario(nome='Part', cpf='111', email='part@test',
                               senha=generate_password_hash('p123'), formacao='F',
                               tipo='participante', cliente_id=cliente.id)
        db.session.add(participante)
        db.session.commit()

        insc_oficina = Inscricao(usuario_id=participante.id, cliente_id=cliente.id,
                                 oficina_id=oficina.id, status_pagamento='approved')
        insc_evento = Inscricao(usuario_id=participante.id, cliente_id=cliente.id,
                                 evento_id=evento.id, status_pagamento='approved')
        db.session.add_all([insc_oficina, insc_evento])
        db.session.commit()

        professor = Usuario(nome='Prof', cpf='222', email='prof@test',
                            senha=generate_password_hash('p123'), formacao='F', tipo='professor')
        db.session.add(professor)
        db.session.commit()

        horario = HorarioVisitacao(evento_id=evento.id, data=date.today(),
                                   horario_inicio=time(9,0), horario_fim=time(10,0),
                                   capacidade_total=30, vagas_disponiveis=30)
        db.session.add(horario)
        db.session.commit()

        agendamento = AgendamentoVisita(
            horario_id=horario.id,
            professor_id=professor.id,
            escola_nome='Escola',
            turma='T1',
            nivel_ensino='fundamental',
            quantidade_alunos=10,
            status='confirmado'
        )
        db.session.add(agendamento)
        db.session.commit()

        aluno = AlunoVisitante(agendamento_id=agendamento.id, nome='Aluno1')
        db.session.add(aluno)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=False)


def test_leitor_checkin_json_success(client, app):
    with app.app_context():
        token = Inscricao.query.filter(Inscricao.evento_id.isnot(None)).first().qr_code_token
        participante = Usuario.query.filter_by(email='part@test').first()
        evento = Evento.query.first()
    login(client, 'cli@test', '123')
    resp = client.post('/leitor_checkin_json', json={'token': token})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    with app.app_context():
        assert Checkin.query.filter_by(usuario_id=participante.id, evento_id=evento.id).count() == 1


def test_leitor_checkin_json_invalid(client, app):
    login(client, 'cli@test', '123')
    resp = client.post('/leitor_checkin_json', json={'token': 'invalid'})
    assert resp.status_code == 404
    assert resp.get_json()['status'] == 'error'


def test_leitor_checkin_json_prefers_oficina(client, app):
    with app.app_context():
        participante = Usuario.query.filter_by(email='part@test').first()
        evento = Evento.query.first()
        oficina = Oficina.query.first()
        insc = Inscricao(usuario_id=participante.id,
                          cliente_id=oficina.cliente_id,
                          oficina_id=oficina.id,
                          evento_id=evento.id,
                          status_pagamento='approved')
        db.session.add(insc)
        db.session.commit()
        token = insc.qr_code_token
    login(client, 'cli@test', '123')
    resp = client.post('/leitor_checkin_json', json={'token': token})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    with app.app_context():
        chk = Checkin.query.filter_by(usuario_id=participante.id, oficina_id=oficina.id).first()
        assert chk is not None
        assert chk.evento_id == evento.id
        assert chk.cliente_id == oficina.cliente_id
    resp = client.get('/lista_checkins_json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(c.get('oficina') == oficina.titulo for c in data['checkins'])


def test_checkin_correct_password(client, app):
    with app.app_context():
        oficina = Oficina.query.first()
        participante = Usuario.query.filter_by(email='part@test').first()
    login(client, 'part@test', 'p123')
    resp = client.post(f'/checkin/{oficina.id}', data={'palavra_escolhida': 'correct'})
    assert resp.status_code == 302
    with app.app_context():
        assert Checkin.query.filter_by(usuario_id=participante.id, oficina_id=oficina.id).count() == 1


def test_checkin_wrong_password(client, app):
    with app.app_context():
        oficina = Oficina.query.first()
        participante = Usuario.query.filter_by(email='part@test').first()
        insc = Inscricao.query.filter_by(oficina_id=oficina.id, usuario_id=participante.id).first()
    login(client, 'part@test', 'p123')
    resp = client.post(f'/checkin/{oficina.id}', data={'palavra_escolhida': 'wrong'})
    assert resp.status_code == 302
    with app.app_context():
        refreshed = Inscricao.query.get(insc.id)
        assert refreshed.checkin_attempts == 1
        assert Checkin.query.filter_by(usuario_id=participante.id, oficina_id=oficina.id).count() == 0


def test_processar_qrcode_success(client, app):
    with app.app_context():
        agendamento = AgendamentoVisita.query.first()
    login(client, 'cli@test', '123')
    resp = client.post('/processar_qrcode', json={'token': agendamento.qr_code_token})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert str(agendamento.id) in data['redirect']


def test_confirmar_checkin_post(client, app):
    with app.app_context():
        agendamento = AgendamentoVisita.query.first()
        aluno = agendamento.alunos[0]
    login(client, 'cli@test', '123')
    resp = client.post(f'/confirmar_checkin/{agendamento.id}', data={'alunos_presentes': str(aluno.id)})
    assert resp.status_code == 302
    with app.app_context():
        ag = AgendamentoVisita.query.get(agendamento.id)
        assert ag.checkin_realizado is True
        assert ag.status == 'realizado'
        assert ag.alunos[0].presente is True
        assert ag.data_checkin is not None


def test_processar_qrcode_invalid(client, app):
    login(client, 'cli@test', '123')
    resp = client.post('/processar_qrcode', json={'token': 'bad'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is False
    assert 'Agendamento n' in data['message']


def test_lista_checkins_json_related_ids(client, app):
    """Check-ins sem cliente_id devem aparecer se vinculados por oficina ou usuário."""
    with app.app_context():
        oficina = Oficina.query.first()
        participante = Usuario.query.filter_by(email='part@test').first()
        professor = Usuario.query.filter_by(email='prof@test').first()

        chk_usuario = Checkin(usuario_id=participante.id,
                              palavra_chave='manual')
        chk_oficina = Checkin(usuario_id=professor.id,
                              oficina_id=oficina.id,
                              palavra_chave='QR-OFICINA')
        db.session.add_all([chk_usuario, chk_oficina])
        db.session.commit()

    login(client, 'cli@test', '123')
    resp = client.get('/lista_checkins_json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    nomes = [c['participante'] for c in data['checkins']]
    assert 'Part' in nomes
    assert 'Prof' in nomes


def test_leitor_checkin_json_other_client_denied(client, app):
    """Check-in deve falhar se o token pertencer a outro cliente."""
    with app.app_context():
        other = Cliente(nome='Other', email='other@test', senha=generate_password_hash('123'))
        db.session.add(other)
        db.session.commit()

        evento = Evento(cliente_id=other.id, nome='E2', habilitar_lotes=False, inscricao_gratuita=True)
        db.session.add(evento)
        db.session.commit()

        participante = Usuario.query.filter_by(email='part@test').first()
        insc = Inscricao(usuario_id=participante.id, cliente_id=other.id,
                         evento_id=evento.id, status_pagamento='approved')
        db.session.add(insc)
        db.session.commit()

        token = insc.qr_code_token

    login(client, 'cli@test', '123')
    resp = client.post('/leitor_checkin_json', json={'token': token})
    assert resp.status_code == 403
    data = resp.get_json()
    assert data['status'] == 'error'
