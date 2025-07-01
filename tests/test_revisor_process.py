import os
import pytest
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from flask import Flask
from flask import render_template
from extensions import db, login_manager

from models import (Cliente, Formulario, CampoFormulario, RevisorProcess,
                    RevisorCandidatura, Usuario, Submission, Assignment)
from routes.auth_routes import auth_routes
from routes.revisor_routes import revisor_routes
from routes.submission_routes import submission_routes
from routes.evento_routes import evento_routes
from routes.peer_review_routes import peer_review_routes
from routes.static_page_routes import static_page_routes
from routes.dashboard_routes import dashboard_routes
import routes.dashboard_cliente  # noqa: F401

@pytest.fixture
def app():
    templates_path = os.path.join(os.path.dirname(__file__), '..', 'templates')
    app = Flask(__name__, template_folder=templates_path)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options('sqlite://')
    app.config['SECRET_KEY'] = 'test'
    login_manager.init_app(app)
    db.init_app(app)

    from models import RevisorProcess
    from flask_login import current_user

    @app.context_processor
    def inject_revisor_process():
        process = None
        if current_user.is_authenticated:
            cliente_id = getattr(current_user, 'cliente_id', None)
            if getattr(current_user, 'tipo', None) == 'cliente':
                cliente_id = current_user.id
            if cliente_id:
                process = RevisorProcess.query.filter_by(cliente_id=cliente_id).first()
        if not process:
            process = RevisorProcess.query.first()
        return {'revisor_process_id': process.id if process else None}

    app.register_blueprint(auth_routes)
    app.register_blueprint(revisor_routes)
    app.register_blueprint(submission_routes)
    app.register_blueprint(evento_routes)
    app.register_blueprint(peer_review_routes)
    app.register_blueprint(static_page_routes)
    app.register_blueprint(dashboard_routes)

    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        form = Formulario(nome='Cand', cliente_id=cliente.id)
        db.session.add(form)
        db.session.commit()
        campo_email = CampoFormulario(formulario_id=form.id, nome='email', tipo='text')
        campo_nome = CampoFormulario(formulario_id=form.id, nome='nome', tipo='text')
        db.session.add_all([campo_email, campo_nome])
        db.session.commit()
        proc = RevisorProcess(cliente_id=cliente.id, formulario_id=form.id, num_etapas=1)
        db.session.add(proc)
        db.session.commit()
        sub = Submission(title='T', locator='loc', code_hash='x')
        db.session.add(sub)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=False)


def test_application_and_approval_flow(client, app):
    with app.app_context():
        proc = RevisorProcess.query.first()
        campos = {c.nome: c.id for c in proc.formulario.campos}
        sub = Submission.query.first()

    resp = client.post(f'/revisor/apply/{proc.id}', data={str(campos['email']): 'rev@test', str(campos['nome']): 'Rev'})
    assert resp.status_code in (302, 200)

    with app.app_context():
        cand = RevisorCandidatura.query.first()
        assert cand.email == 'rev@test'
        cand_id = cand.id
        code = cand.codigo

    resp = client.get(f'/revisor/progress/{code}')
    assert resp.status_code == 200

    login(client, 'cli@test', '123')
    resp = client.post(f'/revisor/approve/{cand_id}', json={})
    assert resp.status_code == 200
    assert resp.get_json()['success']

    with app.app_context():
        cand = RevisorCandidatura.query.get(cand_id)
        assert cand.status == 'aprovado'
        user = Usuario.query.filter_by(email='rev@test').first()
        assert user and user.tipo == 'revisor'
        ass = Assignment.query.filter_by(reviewer_id=user.id).first()
        assert ass is None


def test_navbar_shows_correct_process_id(app):
    with app.app_context():
        proc = RevisorProcess.query.first()
        with app.test_request_context('/'):
            html = render_template('partials/navbar.html')
        assert f'/revisor/apply/{proc.id}' in html
