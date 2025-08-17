import io
import pytest
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from flask import Flask
from extensions import db, login_manager

import sys
import types

# Stub mercadopago to avoid optional dependency issues BEFORE importing routes
mercadopago_stub = types.ModuleType('mercadopago')
mercadopago_stub.SDK = lambda *a, **k: None
sys.modules.setdefault('mercadopago', mercadopago_stub)


    Usuario,
    Cliente,
    Evento,
    Submission,
    Review,
    Assignment,
)
from routes.auth_routes import auth_routes
from routes.trabalho_routes import trabalho_routes
from routes.peer_review_routes import peer_review_routes
from routes.submission_routes import submission_routes
from flask import Blueprint

# Minimal dashboard blueprints used for login redirects
dashboard_routes = Blueprint('dashboard_routes', __name__)

@dashboard_routes.route('/dashboard')
def dashboard():
    return 'dashboard'

@dashboard_routes.route('/dashboard_admin')
def dashboard_admin():
    return 'dashboard admin'

dashboard_professor_bp = Blueprint('dashboard_professor', __name__)

@dashboard_professor_bp.route('/dashboard_professor')
def dashboard_professor():
    return 'dashboard professor'


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options('sqlite://')
    app.secret_key = 'test'

    login_manager.init_app(app)
    db.init_app(app)

    app.register_blueprint(auth_routes)
    app.register_blueprint(trabalho_routes)
    app.register_blueprint(peer_review_routes)
    app.register_blueprint(submission_routes)
    app.register_blueprint(dashboard_routes)
    app.register_blueprint(dashboard_professor_bp)

    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123'))
        admin = Usuario(nome='Admin', cpf='1', email='admin@test', senha=generate_password_hash('123'), formacao='x', tipo='admin')
        reviewer = Usuario(nome='Rev', cpf='2', email='rev@test', senha=generate_password_hash('123'), formacao='x', tipo='professor')
        author = Usuario(nome='Author', cpf='3', email='author@test', senha=generate_password_hash('123'), formacao='x', tipo='participante')
        db.session.add_all([cliente, admin, reviewer, author])
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome='Evento', habilitar_lotes=False, inscricao_gratuita=True)
        db.session.add(evento)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_submission_and_reviewer_flow(client, app):
    resp = client.post('/submissions', data={'title': 'Work', 'content': 'Body', 'email': 'author@test'})
    assert resp.status_code == 201
    payload = resp.get_json()
    locator = payload['locator']
    code = payload['code']

    with app.app_context():
        sub = Submission.query.filter_by(locator=locator).first()

        evento = Evento.query.first()
        author = Usuario.query.filter_by(email='author@test').first()
        sub.evento_id = evento.id
        sub.author_id = author.id
        db.session.commit()

        reviewer = Usuario.query.filter_by(email='rev@test').first()
        sub_id = sub.id
        reviewer_id = reviewer.id

    login(client, 'admin@test', '123')
    resp = client.post('/assign_reviews', json={sub_id: [reviewer_id]})
    assert resp.status_code == 200
    assert resp.get_json()['success']

    with app.app_context():
        rev = Review.query.filter_by(submission_id=sub_id, reviewer_id=reviewer_id).first()
        assert rev and rev.locator
        assert len(rev.access_code) == 8
        access = rev.access_code
        rev_id = rev.id
        loc = rev.locator

    resp = client.post(f'/review/{loc}', data={'codigo': access, 'nota': '7'}, follow_redirects=False)
    assert resp.status_code in (302, 200)

    with app.app_context():
        rev = Review.query.get(rev_id)
        assert rev.finished_at is not None
        assert rev.note == 7
        assignment = Assignment.query.filter_by(submission_id=sub_id, reviewer_id=reviewer_id).first()
        assert assignment.completed is True

    login(client, 'cli@test', '123')
    resp = client.get('/dashboard/client_reviews')
    assert resp.status_code == 200


def test_control_endpoints_and_dashboard_auth(client, app):
    resp = client.post('/submissions', data={'title': 'T', 'content': 'C', 'email': 'x@y.com'})
    assert resp.status_code == 201
    data = resp.get_json()
    locator = data['locator']
    code = data['code']

    resp = client.get(f'/submissions/{locator}?code={code}')
    assert resp.status_code == 200

    resp = client.get(f'/submissions/{locator}/codes')
    assert resp.status_code == 401

    resp = client.get(f'/submissions/{locator}/codes?code={code}')
    assert resp.status_code == 200
    assert resp.get_json()['locator'] == locator

    resp = client.get('/dashboard/reviewer_reviews')
    assert resp.status_code in (302, 401)
