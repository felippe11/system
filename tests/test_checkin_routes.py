import pytest
from werkzeug.security import generate_password_hash
from datetime import date, time
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import (Cliente, Usuario, Evento, Oficina, Inscricao, Ministrante,
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

        agendamento = AgendamentoVisita(horario_id=horario.id, professor_id=professor.id,
                                        escola_nome='Escola', turma='T1',
                                        nivel_ensino='fundamental', quantidade_alunos=10)
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
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


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
