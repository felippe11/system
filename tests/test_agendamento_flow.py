import os
import sys
import types
from datetime import date, time

import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('DB_PASS', 'test')

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
pdf_service_stub.gerar_pdf_relatorio_agendamentos = lambda *a, **k: ''
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

utils_revisor_helpers = types.ModuleType('utils.revisor_helpers')
utils_revisor_helpers.parse_revisor_form = lambda *a, **k: None
utils_revisor_helpers.recreate_stages = lambda *a, **k: None
utils_revisor_helpers.update_process_eventos = lambda *a, **k: None
utils_revisor_helpers.update_revisor_process = lambda *a, **k: None
sys.modules.setdefault('utils.revisor_helpers', utils_revisor_helpers)
utils_stub.revisor_helpers = utils_revisor_helpers

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
    SalaVisitacao,
    AgendamentoVisita,
    AlunoVisitante,
    Inscricao,
    Checkin,
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

        evento = Evento(
            cliente_id=cliente.id,
            nome='Evento',
            habilitar_lotes=False,
            inscricao_gratuita=True,
        )
        db.session.add(evento)
        db.session.commit()

        sala1 = SalaVisitacao(
            nome='Sala 1',
            descricao='Desc',
            capacidade=30,
            evento_id=evento.id,
        )
        sala2 = SalaVisitacao(
            nome='Sala 2',
            descricao='Desc',
            capacidade=30,
            evento_id=evento.id,
        )
        db.session.add_all([sala1, sala2])
        db.session.commit()

        horario1 = HorarioVisitacao(
            evento_id=evento.id,
            data=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(10, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
        )
        horario2 = HorarioVisitacao(
            evento_id=evento.id,
            data=date.today(),
            horario_inicio=time(10, 0),
            horario_fim=time(11, 0),
            capacidade_total=30,
            vagas_disponiveis=30,
        )
        db.session.add_all([horario1, horario2])

        professor = Usuario(
            nome='Prof',
            cpf='222',
            email='prof@test',
            senha=generate_password_hash('p123'),
            formacao='F',
            tipo='professor',
        )
        participante = Usuario(
            nome='Part',
            cpf='333',
            email='part@test',
            senha=generate_password_hash('p123'),
            formacao='F',
            tipo='participante',
        )
        db.session.add_all([professor, participante])
        db.session.commit()

        db.session.add(
            Inscricao(
                usuario_id=participante.id,
                evento_id=evento.id,
                cliente_id=cliente.id,
            )
        )
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
        horario_id = horario.id
        sala = SalaVisitacao.query.first()
        sala_id = sala.id

    resp = client.post(
        f'/professor/criar_agendamento/{horario_id}',
        data={
            'escola_nome': 'Escola X',
            'escola_codigo_inep': '',
            'turma': 'T1',
            'nivel_ensino': 'Fundamental',
            'quantidade_alunos': 5,
            'salas_selecionadas': [str(sala_id)],
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert '/adicionar_alunos/' in resp.headers['Location']
    agendamento_id = int(resp.headers['Location'].rstrip('/').split('/')[-1])

    resp = client.post(f'/professor/adicionar_alunos/{agendamento_id}',
                       data={'nome': 'Aluno 1', 'cpf': '12345678901'},
                       follow_redirects=False)
    assert resp.status_code == 302

    resp = client.get(f'/professor/imprimir_agendamento/{agendamento_id}')
    assert resp.status_code == 302
    assert '/professor/meus_agendamentos' in resp.headers['Location']

    with app.app_context():
        agendamento = AgendamentoVisita.query.get(agendamento_id)
        assert agendamento.professor_id is not None
        assert agendamento.cliente_id is None
        assert agendamento.status == 'pendente'
        assert agendamento.horario_id == horario_id
        assert agendamento.escola_nome == 'Escola X'
        assert agendamento.turma == 'T1'
        assert agendamento.nivel_ensino == 'Fundamental'
        assert agendamento.quantidade_alunos == 5
        assert agendamento.salas_selecionadas == str(sala_id)


def test_cliente_cria_agendamento(app):
    client = app.test_client()

    login(client, 'cli@test', '123')

    with app.app_context():
        horario = HorarioVisitacao.query.first()
        horario_id = horario.id
        sala = SalaVisitacao.query.first()
        sala_id = sala.id

    resp = client.post(
        f'/agendar_visita/{horario_id}',
        data={
            'escola_nome': 'Escola C',
            'turma': 'T1',
            'nivel_ensino': 'Fundamental',
            'quantidade_alunos': 5,
            'salas_selecionadas': [str(sala_id)],
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302

    with app.app_context():
        agendamento = AgendamentoVisita.query.first()
        assert agendamento.cliente_id is not None
        assert agendamento.professor_id is None
        assert agendamento.status == 'pendente'
        assert agendamento.horario_id == horario_id
        assert agendamento.escola_nome == 'Escola C'
        assert agendamento.turma == 'T1'
        assert agendamento.nivel_ensino == 'Fundamental'
        assert agendamento.quantidade_alunos == 5


def test_participante_agendamento_flow(app):
    client = app.test_client()

    login(client, 'part@test', 'p123')

    with app.app_context():
        participante = Usuario.query.filter_by(email='part@test').first()
        horario = HorarioVisitacao.query.first()
        horario_id = horario.id
        sala = SalaVisitacao.query.first()
        sala_id = sala.id
        sala = SalaVisitacao.query.first()
        sala_id = sala.id
        sala = SalaVisitacao.query.first()
        sala_id = sala.id
        sala = SalaVisitacao.query.first()
        sala_id = sala.id
        sala = SalaVisitacao.query.first()
        sala_id = sala.id

    resp = client.post(
        f'/participante/criar_agendamento/{horario_id}',
        data={
            'escola_nome': 'Escola P',
            'escola_codigo_inep': '',
            'turma': 'T1',
            'nivel_ensino': 'Fundamental',
            'quantidade_alunos': 5,
            'salas_selecionadas': [str(sala_id)],
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert '/participante/meus_agendamentos' in resp.headers['Location']

    with app.app_context():
        agendamento = AgendamentoVisita.query.filter_by(
            professor_id=participante.id
        ).first()
        assert agendamento is not None
        assert agendamento.horario_id == horario_id
        assert agendamento.escola_nome == 'Escola P'
        assert agendamento.turma == 'T1'
        assert agendamento.nivel_ensino == 'Fundamental'
        assert agendamento.quantidade_alunos == 5
        assert agendamento.salas_selecionadas == str(sala_id)
        agendamento_id = agendamento.id

    resp = client.get('/participante/meus_agendamentos')
    assert resp.status_code == 200

    resp = client.post(
        f'/participante/cancelar_agendamento/{agendamento_id}',
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app.app_context():
        agendamento = AgendamentoVisita.query.get(agendamento_id)
        assert agendamento.status == 'cancelado'
        assert agendamento.professor_id == participante.id


def test_participante_manage_alunos(app):
    client = app.test_client()

    login(client, 'part@test', 'p123')

    with app.app_context():
        participante = Usuario.query.filter_by(email='part@test').first()
        horario = HorarioVisitacao.query.first()
        horario_id = horario.id
        sala = SalaVisitacao.query.first()
        sala_id = sala.id

    resp = client.post(
        f'/participante/criar_agendamento/{horario_id}',
        data={
            'escola_nome': 'Escola P',
            'escola_codigo_inep': '',
            'turma': 'T1',
            'nivel_ensino': 'Fundamental',
            'quantidade_alunos': 5,
            'salas_selecionadas': [str(sala_id)],
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app.app_context():
        agendamento = AgendamentoVisita.query.filter_by(
            professor_id=participante.id
        ).first()
        agendamento_id = agendamento.id

    resp = client.post(
        f'/participante/adicionar_alunos/{agendamento_id}',
        data={'nome': 'Aluno 1', 'cpf': '12345678901'},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app.app_context():
        aluno = AlunoVisitante.query.filter_by(agendamento_id=agendamento_id).first()
        assert aluno is not None
        aluno_id = aluno.id

    resp = client.post(
        f'/participante/remover_aluno/{aluno_id}',
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app.app_context():
        assert (
            AlunoVisitante.query.filter_by(agendamento_id=agendamento_id).count()
            == 0
        )


def test_participante_cannot_manage_alunos_de_outro(app):
    client = app.test_client()

    login(client, 'part@test', 'p123')

    with app.app_context():
        professor = Usuario.query.filter_by(email='prof@test').first()
        horario = HorarioVisitacao.query.first()
        agendamento = AgendamentoVisita(
            professor_id=professor.id,
            horario_id=horario.id,
            escola_nome='Escola X',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=1,
            salas_selecionadas='1',
        )
        db.session.add(agendamento)
        db.session.commit()
        agendamento_id = agendamento.id

    resp = client.post(
        f'/participante/adicionar_alunos/{agendamento_id}',
        data={'nome': 'Intruso', 'cpf': ''},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert '/participante/meus_agendamentos' in resp.headers['Location']
    with app.app_context():
        assert AlunoVisitante.query.count() == 0

    with app.app_context():
        aluno = AlunoVisitante(agendamento_id=agendamento_id, nome='Aluno')
        db.session.add(aluno)
        db.session.commit()
        aluno_id = aluno.id

    resp = client.post(
        f'/participante/remover_aluno/{aluno_id}',
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert '/participante/meus_agendamentos' in resp.headers['Location']
    with app.app_context():
        assert AlunoVisitante.query.get(aluno_id) is not None


def test_editar_agendamento_shows_current_when_full(app):
    client = app.test_client()

    login(client, 'prof@test', 'p123')

    with app.app_context():
        professor = Usuario.query.filter_by(email='prof@test').first()
        horario1, horario2 = HorarioVisitacao.query.order_by(
            HorarioVisitacao.id
        ).all()
        agendamento = AgendamentoVisita(
            professor_id=professor.id,
            horario_id=horario1.id,
            escola_nome='Escola Y',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=5,
            salas_selecionadas='1',
        )
        db.session.add(agendamento)
        horario1.vagas_disponiveis = 0
        horario2.vagas_disponiveis = 0
        db.session.commit()
        agendamento_id = agendamento.id
        h1_id, h2_id = horario1.id, horario2.id

    resp = client.get(f'/editar_agendamento/{agendamento_id}')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert f'value="{h1_id}"' in html
    assert f'<option value="{h2_id}"' not in html


def test_editar_agendamento_can_change_to_available_slot(app):
    client = app.test_client()

    login(client, 'prof@test', 'p123')

    with app.app_context():
        professor = Usuario.query.filter_by(email='prof@test').first()
        horario1, horario2 = HorarioVisitacao.query.order_by(
            HorarioVisitacao.id
        ).all()
        agendamento = AgendamentoVisita(
            professor_id=professor.id,
            horario_id=horario1.id,
            escola_nome='Escola Z',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=5,
            salas_selecionadas='1',
        )
        db.session.add(agendamento)
        horario1.vagas_disponiveis = 0
        horario2.vagas_disponiveis = 5
        db.session.commit()
        agendamento_id = agendamento.id
        h1_id, h2_id = horario1.id, horario2.id

    resp = client.get(f'/editar_agendamento/{agendamento_id}')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert f'value="{h1_id}"' in html
    assert f'value="{h2_id}"' in html

    resp = client.post(
        f'/editar_agendamento/{agendamento_id}',
        data={
            'horario_id': h2_id,
            'escola_nome': 'Escola Z',
            'escola_codigo_inep': '',
            'turma': 'T1',
            'nivel_ensino': 'Fundamental',
            'quantidade_alunos': '5',
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app.app_context():
        agendamento_atualizado = AgendamentoVisita.query.get(agendamento_id)
        assert agendamento_atualizado.horario_id == h2_id


def test_editar_agendamento_page_renders(app):
    client = app.test_client()

    login(client, 'prof@test', 'p123')

    with app.app_context():
        professor = Usuario.query.filter_by(email='prof@test').first()
        horario = HorarioVisitacao.query.first()
        agendamento = AgendamentoVisita(
            professor_id=professor.id,
            horario_id=horario.id,
            escola_nome='Escola Y',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=5,
            salas_selecionadas='1',
        )
        db.session.add(agendamento)
        db.session.commit()
        agendamento_id = agendamento.id

    resp = client.get(f'/editar_agendamento/{agendamento_id}')
    assert resp.status_code == 200


def test_cancelamento_restaura_vagas(app):
    client = app.test_client()

    login(client, 'prof@test', 'p123')

    with app.app_context():
        professor = Usuario.query.filter_by(email='prof@test').first()
        horario = HorarioVisitacao.query.first()
        horario.vagas_disponiveis = 5
        agendamento = AgendamentoVisita(
            professor_id=professor.id,
            horario_id=horario.id,
            escola_nome='Escola',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=5,
            salas_selecionadas='1',
            status='confirmado',
        )
        db.session.add(agendamento)
        db.session.commit()
        agendamento_id = agendamento.id

    resp = client.put(
        f'/atualizar_status/{agendamento_id}',
        json={'status': 'cancelado'},
    )
    assert resp.status_code == 200

    with app.app_context():
        horario = HorarioVisitacao.query.first()
        assert horario.vagas_disponiveis == 10


def test_cancelamento_limite_capacidade(app):
    client = app.test_client()

    login(client, 'prof@test', 'p123')

    with app.app_context():
        professor = Usuario.query.filter_by(email='prof@test').first()
        horario = HorarioVisitacao.query.first()
        horario.capacidade_total = 8
        horario.vagas_disponiveis = 7
        agendamento = AgendamentoVisita(
            professor_id=professor.id,
            horario_id=horario.id,
            escola_nome='Escola',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=5,
            salas_selecionadas='1',
            status='confirmado',
        )
        db.session.add(agendamento)
        db.session.commit()
        agendamento_id = agendamento.id

    resp = client.put(
        f'/atualizar_status/{agendamento_id}',
        json={'status': 'cancelado'},
    )
    assert resp.status_code == 200

    with app.app_context():
        horario = HorarioVisitacao.query.first()
        assert horario.vagas_disponiveis == 8


def test_confirmar_checkin_cria_checkin(app):
    client = app.test_client()

    login(client, 'cli@test', '123')

    with app.app_context():
        cliente = Cliente.query.filter_by(email='cli@test').first()
        professor = Usuario.query.filter_by(email='prof@test').first()
        horario = HorarioVisitacao.query.first()
        agendamento = AgendamentoVisita(
            professor_id=professor.id,
            cliente_id=cliente.id,
            horario_id=horario.id,
            escola_nome='Escola',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=5,
            salas_selecionadas='1',
            status='confirmado',
        )
        db.session.add(agendamento)
        db.session.commit()
        token = agendamento.qr_code_token
        agendamento_id = agendamento.id
        evento_id = horario.evento_id
        cliente_id = cliente.id

    resp = client.post(
        f'/confirmar_checkin_agendamento/{token}',
        data={},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app.app_context():
        agendamento = AgendamentoVisita.query.get(agendamento_id)
        assert agendamento.checkin_realizado is True
        chk = Checkin.query.filter_by(
            usuario_id=agendamento.professor_id,
            evento_id=evento_id,
            cliente_id=cliente_id,
            palavra_chave='QR-AGENDAMENTO',
        ).first()
        assert chk is not None


def test_checkin_agendamento_cria_checkin(app):
    client = app.test_client()

    login(client, 'prof@test', 'p123')

    with app.app_context():
        cliente = Cliente.query.filter_by(email='cli@test').first()
        professor = Usuario.query.filter_by(email='prof@test').first()
        horario = HorarioVisitacao.query.first()
        agendamento = AgendamentoVisita(
            professor_id=professor.id,
            cliente_id=cliente.id,
            horario_id=horario.id,
            escola_nome='Escola',
            turma='T1',
            nivel_ensino='Fundamental',
            quantidade_alunos=5,
            salas_selecionadas='1',
            status='confirmado',
        )
        db.session.add(agendamento)
        db.session.commit()
        token = agendamento.qr_code_token
        agendamento_id = agendamento.id
        evento_id = horario.evento_id
        cliente_id = cliente.id

    resp = client.post(f'/checkin/{token}')
    assert resp.status_code == 200

    with app.app_context():
        agendamento = AgendamentoVisita.query.get(agendamento_id)
        assert agendamento.checkin_realizado is True
        chk = Checkin.query.filter_by(
            usuario_id=agendamento.professor_id,
            evento_id=evento_id,
            cliente_id=cliente_id,
            palavra_chave='QR-AGENDAMENTO',
        ).first()
        assert chk is not None
