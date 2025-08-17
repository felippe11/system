import os
import types
import pytest
from werkzeug.security import generate_password_hash
from datetime import date
from unittest.mock import patch
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from flask import Flask, Blueprint
from extensions import db, login_manager, csrf
from models import Evento, Oficina, OficinaDia
from models.user import Cliente, Usuario
from routes.auth_routes import auth_routes
from routes.dashboard_participante import dashboard_participante_routes, dashboard_participante
from routes.inscricao_routes import inscricao_routes

revisor_routes = Blueprint('revisor_routes', __name__)

@revisor_routes.route('/processo_seletivo')
def select_event():
    return 'ok'

@revisor_routes.route('/revisor/progress')
def progress_query():
    return 'ok'

peer_review_routes = Blueprint('peer_review_routes', __name__)

@peer_review_routes.route('/reviewer_dashboard', methods=['POST'])
def reviewer_dashboard():
    return 'ok'

evento_routes = Blueprint('evento_routes', __name__)

@evento_routes.route('/')
def home():
    return 'home'


dashboard_routes = Blueprint('dashboard_routes', __name__)

@dashboard_routes.route('/dashboard')
def dashboard():
    return 'dashboard'


@pytest.fixture
def app():
    templates_root = os.path.join(os.path.dirname(__file__), '..', 'templates')
    app = Flask(__name__, template_folder=templates_root)
    app.jinja_loader.searchpath.append(os.path.join(templates_root, 'dashboard'))
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options('sqlite://')
    app.secret_key = 'test'

    login_manager.init_app(app)
    db.init_app(app)
    csrf.init_app(app)

    app.register_blueprint(auth_routes)
    app.register_blueprint(dashboard_routes)
    app.register_blueprint(evento_routes)
    app.register_blueprint(inscricao_routes)
    app.register_blueprint(peer_review_routes)
    app.register_blueprint(revisor_routes)
    app.register_blueprint(dashboard_participante_routes)

    with app.app_context():
        db.create_all()
        c1 = Cliente(nome='C1', email='c1@test', senha=generate_password_hash('1'))
        c2 = Cliente(nome='C2', email='c2@test', senha=generate_password_hash('1'))
        db.session.add_all([c1, c2])
        db.session.commit()
        ev = Evento(cliente_id=c2.id, nome='Public Event', inscricao_gratuita=True, publico=True)
        db.session.add(ev)
        db.session.commit()
        ofi = Oficina(
            titulo='Of1', descricao='d', ministrante_id=None,
            vagas=10, carga_horaria='1', estado='SP', cidade='SP',
            cliente_id=c2.id, evento_id=ev.id
        )
        db.session.add(ofi)
        db.session.flush()
        dia = OficinaDia(oficina_id=ofi.id, data=date.today(), horario_inicio='08:00', horario_fim='10:00')
        db.session.add(dia)
        user = Usuario(
            nome='U', cpf='1', email='p@test', senha=generate_password_hash('123'),
            formacao='x', tipo='participante', cliente_id=c1.id
        )
        db.session.add(user)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_public_event_visible_to_participant(app):
    with app.test_request_context('/dashboard_participante'):
        from flask_login import login_user, logout_user
        user = Usuario.query.filter_by(email='p@test').first()
        login_user(user)
        with patch('routes.dashboard_participante.render_template') as rt:
            rt.side_effect = lambda tpl, **ctx: ctx
            ctx = dashboard_participante()
        logout_user()
    nomes = [e.nome for e in ctx['eventos_sorted']]
    assert 'Public Event' not in nomes
