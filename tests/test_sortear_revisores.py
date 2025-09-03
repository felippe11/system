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
            senha=generate_password_hash('123', method="pbkdf2:sha256"),
        )
        db.session.add(cliente)
        db.session.commit()
        db.session.add(
            ConfiguracaoCliente(
                cliente_id=cliente.id,
                max_trabalhos_por_revisor=2,
                num_revisores_max=1,
            )
        )
        evento = Evento(cliente_id=cliente.id, nome='E1')
        db.session.add(evento)
        db.session.flush()
        proc = RevisorProcess(
            cliente_id=cliente.id,
            nome="Proc",
            status="ativo",
        )
        db.session.add(proc)
        db.session.flush()
        proc.eventos.append(evento)
        db.session.add(
            RevisorCandidatura(
                process_id=proc.id,
                status='aprovado',
                email='rev1@example.com',
                respostas={'area': 'bio'},
            )
        )
        db.session.add(
            RevisorCandidatura(
                process_id=proc.id,
                status='aprovado',
                email='rev2@example.com',
                respostas={'area': 'bio'},
            )
        )
        db.session.add(
            Usuario(
                nome='Rev1',
                cpf='1',
                email='rev1@example.com',
                senha=generate_password_hash('123', method="pbkdf2:sha256"),
                formacao='',
                tipo='revisor',
            )
        )
        db.session.add(
            Usuario(
                nome='Rev2',
                cpf='2',
                email='rev2@example.com',
                senha=generate_password_hash('123', method="pbkdf2:sha256"),
                formacao='',
                tipo='revisor',
            )
        )
        db.session.add(Submission(title='S1', code_hash='h1', evento_id=evento.id))
        db.session.add(Submission(title='S2', code_hash='h2', evento_id=evento.id))
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_sortear_revisores_limits(client, app):
    login(client, 'cli@example.com', '123')
    resp = client.post(
        '/assign_by_filters',
        json={'filters': {'area': 'bio'}, 'limit': 1, 'max_per_submission': 1},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success']
    with app.app_context():
        assert Assignment.query.count() == 2
        for r in Usuario.query.filter(Usuario.email.like('rev%')).all():
            assert Assignment.query.filter_by(reviewer_id=r.id).count() <= 1
        for s in Submission.query.all():
            assert Assignment.query.filter_by(submission_id=s.id).count() <= 1
