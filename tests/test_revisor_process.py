import pytest
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from flask import Flask
from extensions import db, login_manager

from models import (Cliente, Formulario, CampoFormulario, RevisorProcess,
                    RevisorCandidatura, Usuario, Submission, Assignment)
from routes.auth_routes import auth_routes
from routes.revisor_routes import revisor_routes
from routes.submission_routes import submission_routes

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options('sqlite://')
    login_manager.init_app(app)
    db.init_app(app)

    app.register_blueprint(auth_routes)
    app.register_blueprint(revisor_routes)
    app.register_blueprint(submission_routes)

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
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


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
    resp = client.post(f'/revisor/approve/{cand_id}', json={'submission_id': sub.id})
    assert resp.status_code == 200
    assert resp.get_json()['success']

    with app.app_context():
        cand = RevisorCandidatura.query.get(cand_id)
        assert cand.status == 'aprovado'
        user = Usuario.query.filter_by(email='rev@test').first()
        assert user and user.tipo == 'revisor'
        ass = Assignment.query.filter_by(submission_id=sub.id, reviewer_id=user.id).first()
        assert ass is not None
