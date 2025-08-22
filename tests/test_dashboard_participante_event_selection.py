import os
import pytest
from werkzeug.security import generate_password_hash
from datetime import date
from unittest.mock import patch
from config import Config
from flask import Flask, Blueprint
from extensions import db, login_manager, csrf
from models import Evento, Inscricao
from models.user import Cliente, Usuario

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')

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
        c1 = Cliente(nome='C1', email='c1@test', senha=generate_password_hash('1', method="pbkdf2:sha256"))
        c2 = Cliente(nome='C2', email='c2@test', senha=generate_password_hash('1', method="pbkdf2:sha256"))
        db.session.add_all([c1, c2])
        db.session.commit()
        ev1 = Evento(cliente_id=c2.id, nome='Event1', inscricao_gratuita=True, publico=True, data_inicio=date(2024,1,1))
        ev2 = Evento(cliente_id=c2.id, nome='Event2', inscricao_gratuita=True, publico=True, data_inicio=date(2024,6,1))
        db.session.add_all([ev1, ev2])
        db.session.commit()
        user = Usuario(
            nome='U', cpf='1', email='p@test', senha=generate_password_hash('123', method="pbkdf2:sha256"),
            formacao='x', tipo='participante', cliente_id=c1.id
        )
        db.session.add(user)
        db.session.flush()
        ins1 = Inscricao(usuario_id=user.id, cliente_id=c2.id, evento_id=ev1.id)
        ins2 = Inscricao(usuario_id=user.id, cliente_id=c2.id, evento_id=ev2.id)
        db.session.add_all([ins1, ins2])
        db.session.commit()
        app.user_id = user.id
        app.ev1_id = ev1.id
        app.ev2_id = ev2.id
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_dashboard_selects_latest_event_by_default(app):
    from flask_login import login_user, logout_user
    with app.test_request_context('/dashboard_participante'):
        user = Usuario.query.get(app.user_id)
        login_user(user)
        with patch('routes.dashboard_participante.render_template') as rt:
            rt.side_effect = lambda tpl, **ctx: ctx
            ctx = dashboard_participante()
        logout_user()
    assert ctx['evento'].id == app.ev2_id
    assert [e.id for e in ctx['eventos_sorted']] == [app.ev2_id, app.ev1_id]


def test_dashboard_respects_evento_id_param(app):
    from flask_login import login_user, logout_user
    with app.test_request_context('/dashboard_participante', query_string={'evento_id': app.ev1_id}):
        user = Usuario.query.get(app.user_id)
        login_user(user)
        with patch('routes.dashboard_participante.render_template') as rt:
            rt.side_effect = lambda tpl, **ctx: ctx
            ctx = dashboard_participante()
        logout_user()
    assert ctx['evento'].id == app.ev1_id
