import os
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")
import pytest
from flask import Flask, Blueprint, get_flashed_messages
from unittest.mock import patch
from sqlalchemy.exc import ProgrammingError
from config import Config
from extensions import db, login_manager, csrf
from models.user import Cliente, Usuario
from routes.dashboard_participante import dashboard_participante_routes, dashboard_participante
from routes.formularios_routes import formularios_routes, listar_formularios


@pytest.fixture
def app():
    templates_root = os.path.join(os.path.dirname(__file__), '..', 'templates')
    app = Flask(__name__, template_folder=templates_root)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options('sqlite://')
    app.secret_key = 'test'

    login_manager.init_app(app)
    db.init_app(app)
    csrf.init_app(app)

    dashboard_routes = Blueprint('dashboard_routes', __name__)

    @dashboard_routes.route('/dashboard')
    def dashboard():
        return 'dashboard'

    app.register_blueprint(dashboard_routes)
    app.register_blueprint(dashboard_participante_routes)
    app.register_blueprint(formularios_routes)

    with app.app_context():
        db.create_all()
        cli = Cliente(nome='Cli', email='cli@test', senha='1')
        db.session.add(cli)
        db.session.flush()
        user = Usuario(nome='U', cpf='1', email='u@test', senha='1', formacao='x', tipo='participante', cliente_id=cli.id)
        db.session.add(user)
        db.session.commit()
        app.user_id = user.id
    yield app


def test_dashboard_participante_handles_missing_formulario_columns(app):
    from flask_login import login_user, logout_user
    with app.test_request_context('/dashboard_participante'):
        user = Usuario.query.get(app.user_id)
        login_user(user)
        with patch('routes.dashboard_participante.Formulario') as FormMock, \
             patch('routes.dashboard_participante.render_template') as rt:
            FormMock.query.filter_by.side_effect = ProgrammingError('stmt', None, Exception('orig'))
            rt.side_effect = lambda tpl, **ctx: ctx
            ctx = dashboard_participante()
        messages = get_flashed_messages(with_categories=True)
        logout_user()
    assert ctx['formularios_disponiveis'] is False
    assert any(cat == 'danger' for cat, _ in messages)


def test_listar_formularios_handles_programming_error(app):
    from flask_login import login_user, logout_user
    
    with app.test_request_context('/formularios'):
        user = Usuario.query.get(app.user_id)
        login_user(user)
        with patch('routes.formularios_routes.Formulario.query') as query_mock,              patch('routes.formularios_routes.render_template') as rt:
            query_mock.options.side_effect = ProgrammingError('stmt', None, Exception('orig'))
            rt.side_effect = lambda tpl, **ctx: ctx
            ctx = listar_formularios()
        messages = get_flashed_messages(with_categories=True)
        logout_user()
    assert ctx['formularios'] == []
    assert any(cat == 'danger' for cat, _ in messages)

