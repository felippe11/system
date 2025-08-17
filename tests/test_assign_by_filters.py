import os

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
from werkzeug.security import generate_password_hash
import pytest
from config import Config


Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import (
    Cliente,
    ConfiguracaoCliente,
    RevisorProcess,
    RevisorCandidatura,
    Submission,
    Usuario,
    Assignment,
    AuditLog,
    Evento,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome='Cli',
            email='cli@example.com',
            senha=generate_password_hash('123'),
        )
        db.session.add(cliente)
        db.session.commit()
        db.session.add(
            ConfiguracaoCliente(
                cliente_id=cliente.id, max_trabalhos_por_revisor=2
            )
        )
        evento1 = Evento(cliente_id=cliente.id, nome='E1')
        evento2 = Evento(cliente_id=cliente.id, nome='E2')
        db.session.add_all([evento1, evento2])
        db.session.flush()
        proc = RevisorProcess(cliente_id=cliente.id)
        db.session.add(proc)
        db.session.flush()
        proc.eventos.append(evento1)
        db.session.add(
            RevisorCandidatura(
                process_id=proc.id,
                status='aprovado',
                email='rev@example.com',
                respostas={'area': 'bio'},
            )
        )
        db.session.add(
            Usuario(
                nome='Rev',
                cpf='1',
                email='rev@example.com',
                senha=generate_password_hash('123'),
                formacao='',
                tipo='revisor',
            )
        )
        db.session.add(
            Submission(title='S1', code_hash='h', evento_id=evento1.id)
        )
        db.session.add(
            Submission(title='S2', code_hash='h2', evento_id=evento2.id)
        )
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_assign_by_filters(client, app):
    login(client, 'cli@example.com', '123')
    resp = client.post(
        '/assign_by_filters',
        json={'filters': {'area': 'bio'}, 'limit': 1},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success']
    with app.app_context():
        sub1 = Submission.query.filter_by(title='S1').first()
        sub2 = Submission.query.filter_by(title='S2').first()
        assert Assignment.query.count() == 1
        ass = Assignment.query.first()
        assert ass.submission_id == sub1.id
        assert not sub2.assignments
        assert AuditLog.query.filter_by(
            submission_id=ass.submission_id, event_type='assignment'
        ).count() == 1


def test_assign_by_filters_max_per_submission(client, app):
    login(client, 'cli@example.com', '123')
    with app.app_context():
        proc = RevisorProcess.query.first()
        evento2 = Evento.query.filter_by(nome='E2').first()
        proc.eventos.append(evento2)
        reviewer = Usuario.query.filter_by(email='rev@example.com').first()
        sub1 = Submission.query.filter_by(title='S1').first()
        db.session.add(Assignment(submission_id=sub1.id, reviewer_id=reviewer.id))
        db.session.commit()
    resp = client.post(
        '/assign_by_filters',
        json={'filters': {'area': 'bio'}, 'limit': 1, 'max_per_submission': 1},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success']
    assert data['assignments'] == 1
    with app.app_context():
        sub1 = Submission.query.filter_by(title='S1').first()
        sub2 = Submission.query.filter_by(title='S2').first()
        assert len(sub1.assignments) == 1
        assert len(sub2.assignments) == 1
