import pytest
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db

    Cliente,
    Evento,
    Usuario,
    ConfiguracaoCliente,
    Formulario,
    CampoFormulario,
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
        evento = Evento(cliente_id=cliente.id, nome='EV', submissao_aberta=False)
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
        form = Formulario(
            nome='FSub', cliente_id=cliente.id, is_submission_form=True
        )
        db.session.add(form)
        db.session.commit()
        campo = CampoFormulario(
            formulario_id=form.id,
            nome='Arquivo',
            tipo='file',
            obrigatorio=True,
        )
        db.session.add(campo)
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


def test_toggle_submissao_evento(client, app):
    with app.app_context():
        evento = Evento.query.first()
    login(client, 'cli@test', '123')
    resp = client.post(f'/toggle_submissao_evento/{evento.id}')
    assert resp.status_code == 200
    with app.app_context():
        assert Evento.query.get(evento.id).submissao_aberta is True
    client.post(f'/toggle_submissao_evento/{evento.id}')
    with app.app_context():
        assert Evento.query.get(evento.id).submissao_aberta is False


def test_form_without_event_field(client, app):
    with app.app_context():
        evento = Evento.query.first()
        evento.submissao_aberta = True
        db.session.commit()
    login(client, 'part@test', '123')
    resp = client.get('/submeter_trabalho')
    assert resp.status_code == 200
    assert b'name="evento_id"' not in resp.data
