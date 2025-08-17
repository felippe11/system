import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Evento, Formulario
from models.user import Cliente, Usuario

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        c1 = Cliente(nome='C1', email='c1@test', senha=generate_password_hash('123'))
        c2 = Cliente(nome='C2', email='c2@test', senha=generate_password_hash('123'))
        db.session.add_all([c1, c2])
        db.session.commit()
        f1 = Formulario(nome='F1', cliente_id=c1.id)
        f2 = Formulario(nome='F2', cliente_id=c2.id)
        ev = Evento(cliente_id=c2.id, nome='EV', inscricao_gratuita=True, publico=True)
        db.session.add_all([f1, f2, ev])
        db.session.commit()
        ev.formularios.append(f2)
        db.session.commit()
        p1 = Usuario(nome='Part1', cpf='1', email='p1@test', senha=generate_password_hash('123'), formacao='x', tipo='participante', cliente_id=c1.id, evento_id=ev.id)
        p2 = Usuario(nome='Part2', cpf='2', email='p2@test', senha=generate_password_hash('123'), formacao='x', tipo='participante', cliente_id=c1.id)
        db.session.add_all([p1, p2])
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_cross_client_event_forms_visible(client, app):
    with app.app_context():
        evento = Evento.query.filter_by(nome='EV').first()
    login(client, 'p1@test', '123')
    resp = client.get(f'/formularios_participante?evento_id={evento.id}')
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    assert 'F2' in data
    assert 'F1' not in data


def test_default_behavior_same_client(client, app):
    login(client, 'p2@test', '123')
    resp = client.get('/formularios_participante')
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    assert 'F1' in data
    assert 'F2' not in data
