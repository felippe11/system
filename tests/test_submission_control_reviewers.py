import os
import io
import pytest
import pandas as pd
from werkzeug.security import generate_password_hash

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
os.environ.setdefault('DB_PASS', 'x')

from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import Usuario, Cliente, RevisorProcess, RevisorCandidatura, Submission


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        admin = Usuario(
            nome='Admin',
            cpf='1',
            email='admin@test',
            senha=generate_password_hash('123', method="pbkdf2:sha256"),
            formacao='',
            tipo='admin',
        )
        cliente = Cliente(
            nome='Cli',
            email='cli@test',
            senha=generate_password_hash('123', method="pbkdf2:sha256"),
        )
        db.session.add_all([admin, cliente])
        db.session.flush()
        proc = RevisorProcess(cliente_id=cliente.id)
        db.session.add(proc)
        db.session.flush()
        db.session.add_all(
            [
                Usuario(
                    nome='Aprovado',
                    cpf='2',
                    email='aprovado@test',
                    senha=generate_password_hash('123', method="pbkdf2:sha256"),
                    formacao='',
                    tipo='revisor',
                ),
                Usuario(
                    nome='Pendente',
                    cpf='3',
                    email='pendente@test',
                    senha=generate_password_hash('123', method="pbkdf2:sha256"),
                    formacao='',
                    tipo='revisor',
                ),
            ]
        )
        db.session.add_all(
            [
                RevisorCandidatura(
                    process_id=proc.id,
                    status='aprovado',
                    email='aprovado@test',
                ),
                RevisorCandidatura(
                    process_id=proc.id,
                    status='pendente',
                    email='pendente@test',
                ),
            ]
        )
        db.session.add(Submission(title='S1', code_hash='h'))
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post('/login', data={'email': 'admin@test', 'senha': '123'}, follow_redirects=True)


def test_submission_control_lists_only_approved_reviewers(client, app):
    login(client)
    resp = client.get('/submissoes/controle')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Aprovado' in html
    assert 'Pendente' not in html
    assert 'Nenhum revisor aprovado' not in html


def test_submission_control_shows_placeholder_when_no_approved(client, app):
    with app.app_context():
        cand = RevisorCandidatura.query.filter_by(email='aprovado@test').first()
        cand.status = 'pendente'
        db.session.commit()
    login(client)
    resp = client.get('/submissoes/controle')
    html = resp.get_data(as_text=True)
    assert 'Nenhum revisor aprovado' in html


def test_importar_trabalhos_aparece_na_tabela(client, app):
    login(client)
    df = pd.DataFrame({'title': ['Trabalho Y']})
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    resp = client.post(
        '/importar_trabalhos',
        data={'arquivo': (buffer, 'dados.xlsx')},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 200
    resp = client.get('/submissoes/controle')
    assert resp.status_code == 200
    assert b'Trabalho Y' in resp.data
