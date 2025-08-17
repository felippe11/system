import io
import pytest
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import (
    Cliente,
    Evento,
    Usuario,
    ConfiguracaoCliente,
    Formulario,

    CampoFormulario,

    RespostaFormulario,
    Submission,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123'))
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome='EV', submissao_aberta=True)
        db.session.add(evento)
        db.session.commit()
        usuario = Usuario(
            nome='Part',
            cpf='1',
            email='part@test',
            senha=generate_password_hash('123'),
            formacao='x',
            tipo='participante',
            cliente_id=cliente.id,
            evento_id=evento.id,
        )
        db.session.add(usuario)
        db.session.commit()
        form = Formulario(nome='FSub', cliente_id=cliente.id, is_submission_form=True)
        db.session.add(form)
        db.session.commit()
        campo_text = CampoFormulario(
            formulario_id=form.id, nome='Titulo', tipo='text'
        )
        db.session.add(campo_text)
        db.session.commit()
        campo_file = CampoFormulario(
            formulario_id=form.id, nome='Arquivo', tipo='file', obrigatorio=True
        )
        db.session.add(campo_file)
        db.session.commit()
        config = ConfiguracaoCliente(
            cliente_id=cliente.id,
            formulario_submissao_id=form.id,
            habilitar_submissao_trabalhos=True,
        )
        db.session.add(config)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_get_submission_form(client, app):
    login(client, 'part@test', '123')
    resp = client.get('/submeter_trabalho')
    assert resp.status_code == 200
    with app.app_context():
        campo = CampoFormulario.query.filter_by(tipo='file').first()
        assert f'name="file_{campo.id}"'.encode() in resp.data


def test_submission_creates_record(client, app):
    login(client, 'part@test', '123')
    with app.app_context():
        campo_text = CampoFormulario.query.filter_by(tipo='text').first()
        campo_file = CampoFormulario.query.filter_by(tipo='file').first()
    data = {
        str(campo_text.id): 'Meu Titulo',
        f'file_{campo_file.id}': (io.BytesIO(b'PDF'), 'teste.pdf'),
    }
    resp = client.post(
        '/submeter_trabalho',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert Submission.query.count() == 1

        assert RespostaFormulario.query.count() == 1

