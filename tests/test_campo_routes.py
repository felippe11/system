import pytest
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)
from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models import CampoPersonalizadoCadastro, Evento, ConfiguracaoCliente, ConfiguracaoEvento
from models.user import Usuario, Cliente
import os
import tempfile
from unittest.mock import patch

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_adicionar_campo_personalizado_unauthorized(client, app):
    with app.app_context():
        cliente = Cliente(nome='Cli', email='cli@example.com', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome='EV')
        user = Usuario(nome='User', cpf='1', email='u@example.com', senha=generate_password_hash('123'), formacao='x')
        db.session.add_all([user, evento])
        db.session.commit()

    login(client, 'u@example.com', '123')
    resp = client.post('/adicionar_campo_personalizado', data={'nome_campo': 'Campo', 'tipo_campo': 'texto', 'obrigatorio': 'on', 'evento_id': evento.id}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Acesso negado' in resp.data
    with app.app_context():
        assert CampoPersonalizadoCadastro.query.count() == 0


def test_remover_campo_personalizado_unauthorized(client, app):
    with app.app_context():
        cliente = Cliente(nome='Cli', email='c@example.com', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome='EV')
        campo = CampoPersonalizadoCadastro(cliente_id=cliente.id, evento_id=evento.id, nome='C', tipo='texto')
        user = Usuario(nome='User', cpf='2', email='user2@example.com', senha=generate_password_hash('123'), formacao='y')
        db.session.add_all([evento, campo, user])
        db.session.commit()
        field_id = campo.id

    login(client, 'user2@example.com', '123')
    resp = client.post(f'/remover_campo_personalizado/{field_id}', data={'evento_id': evento.id}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Acesso negado' in resp.data
    with app.app_context():
        assert CampoPersonalizadoCadastro.query.get(field_id) is not None


def test_preview_certificado_logged_in(client, app):
    with app.app_context():
        cliente = Cliente(nome='Cli', email='cli@example.com', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        cid = cliente.id

    dummy = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    dummy.write(b'PDF')
    dummy.close()

    with patch('routes.certificado_routes.gerar_certificado_personalizado', return_value=dummy.name):
        login(client, 'cli@example.com', '123')
        resp = client.get('/preview_certificado')
        assert resp.status_code == 200
        assert resp.mimetype == 'application/pdf'
    os.remove(dummy.name)


import pytest

@pytest.mark.parametrize('route,field,default,event_based', [
    ('/toggle_checkin_global_cliente', 'permitir_checkin_global', False, True),
    ('/toggle_feedback_cliente', 'habilitar_feedback', False, True),
    ('/toggle_certificado_cliente', 'habilitar_certificado_individual', False, True),
    ('/toggle_qrcode_evento_credenciamento', 'habilitar_qrcode_evento_credenciamento', False, True),
    ('/toggle_submissao_trabalhos', 'habilitar_submissao_trabalhos', False, False),
    ('/toggle_mostrar_taxa', 'mostrar_taxa', True, False),
])
def test_toggle_default_fields(client, app, route, field, default, event_based):
    with app.app_context():
        # Cria cliente e evento
        cliente = Cliente(nome='Cli', email='toggler@example.com', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome='EV')
        db.session.add(evento)
        db.session.commit()

        # Cria configurações padrão
        db.session.add(ConfiguracaoCliente(cliente_id=cliente.id))
        db.session.add(ConfiguracaoEvento(evento_id=evento.id))
        db.session.commit()

        cid = cliente.id
        eid = evento.id

    login(client, 'toggler@example.com', '123')
    data = {'evento_id': eid} if event_based else {}
    resp = client.post(route, json=data)
    assert resp.status_code == 200

    with app.app_context():
        if event_based:
            cfg = ConfiguracaoEvento.query.filter_by(evento_id=eid).first()
        else:
            cfg = ConfiguracaoCliente.query.filter_by(cliente_id=cid).first()
        assert getattr(cfg, field) == (not default)



@pytest.mark.parametrize('route,field,default', [
    ('/toggle_checkin_global_cliente', 'permitir_checkin_global', False),
    ('/toggle_feedback_cliente', 'habilitar_feedback', False),
    ('/toggle_certificado_cliente', 'habilitar_certificado_individual', False),
    ('/toggle_qrcode_evento_credenciamento', 'habilitar_qrcode_evento_credenciamento', False),
    ('/toggle_submissao_trabalhos', 'habilitar_submissao_trabalhos', False),
    ('/toggle_mostrar_taxa', 'mostrar_taxa', True),
])
def test_toggle_event_isolated(client, app, route, field, default):
    with app.app_context():
        cliente = Cliente(nome='Cli', email='iso@example.com', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        evento1 = Evento(cliente_id=cliente.id, nome='EV1')
        evento2 = Evento(cliente_id=cliente.id, nome='EV2')
        db.session.add_all([evento1, evento2])
        db.session.commit()
        db.session.add(ConfiguracaoCliente(cliente_id=cliente.id))
        db.session.add_all([ConfiguracaoEvento(evento_id=evento1.id), ConfiguracaoEvento(evento_id=evento2.id)])
        db.session.commit()
        eid1 = evento1.id
        eid2 = evento2.id
    login(client, 'iso@example.com', '123')
    client.post(route, query_string={'evento_id': eid1})
    with app.app_context():
        cfg1 = ConfiguracaoEvento.query.filter_by(evento_id=eid1).first()
        cfg2 = ConfiguracaoEvento.query.filter_by(evento_id=eid2).first()
        assert getattr(cfg1, field) == (not default)
        assert getattr(cfg2, field) == default

