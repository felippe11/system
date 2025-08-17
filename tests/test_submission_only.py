import types
import pytest
from werkzeug.security import generate_password_hash
from datetime import date
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Evento, EventoInscricaoTipo, Oficina, OficinaDia
from models.user import Cliente, Usuario, LinkCadastro

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha='1')
        db.session.add(cliente)
        db.session.commit()
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def _setup_event(app):
    with app.app_context():
        cliente = Cliente.query.first()
        evento = Evento(cliente_id=cliente.id, nome='EV', habilitar_lotes=False, inscricao_gratuita=False)
        db.session.add(evento)
        db.session.commit()
        tipo = EventoInscricaoTipo(evento_id=evento.id, nome='Autor', preco=10.0, submission_only=True)
        db.session.add(tipo)
        db.session.commit()
        link = LinkCadastro(cliente_id=cliente.id, evento_id=evento.id, token='tok')
        db.session.add(link)
        oficina = Oficina(titulo='Of1', descricao='d', ministrante_id=None, vagas=10, carga_horaria='1', estado='SP', cidade='SP', cliente_id=cliente.id, evento_id=evento.id)
        db.session.add(oficina)
        db.session.flush()
        dia = OficinaDia(oficina_id=oficina.id, data=date.today(), horario_inicio='08:00', horario_fim='10:00')
        db.session.add(dia)
        db.session.commit()
        user = Usuario(nome='U', cpf='1', email='u@test', senha=generate_password_hash('123'), formacao='x', tipo='participante', cliente_id=cliente.id, evento_id=evento.id, tipo_inscricao_id=tipo.id)
        db.session.add(user)
        db.session.commit()
        return evento.id, link.token, user.email


def test_submission_only_type_creation(app):
    with app.app_context():
        cliente = Cliente.query.first()
        evento = Evento(cliente_id=cliente.id, nome='E', habilitar_lotes=False, inscricao_gratuita=True)
        db.session.add(evento)
        db.session.commit()
        tipo = EventoInscricaoTipo(evento_id=evento.id, nome='Autor', preco=0.0, submission_only=True)
        db.session.add(tipo)
        db.session.commit()
        assert EventoInscricaoTipo.query.get(tipo.id).submission_only is True


def test_registration_shows_submission_only_type(client, app):
    evento_id, token, email = _setup_event(app)
    resp = client.get(f'/inscricao/{token}')
    assert b'Autor' in resp.data


def test_dashboard_hides_workshops_for_submission_only(client, app):
    evento_id, token, email = _setup_event(app)
    login(client, email, '123')
    resp = client.get('/dashboard_participante')
    assert b'Of1' not in resp.data
