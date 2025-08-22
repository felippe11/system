import pytest
from werkzeug.security import generate_password_hash
import pytest
from werkzeug.security import generate_password_hash

from config import Config
from app import create_app
from extensions import db
from models import Evento
from models.user import Usuario, Cliente

Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    with app.app_context():
        db.create_all()
        cliente = Cliente(
            nome="Cli", email="cli@test", senha=generate_password_hash("123", method="pbkdf2:sha256")
        )
        db.session.add(cliente)
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome="EV")
        db.session.add(evento)
        usuario = Usuario(
            id=cliente.id,
            nome="CliUser",
            cpf="1",
            email="cli@test",
            senha=generate_password_hash("123", method="pbkdf2:sha256"),
            formacao="x",
            tipo="cliente",
        )
        db.session.add(usuario)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post(
        '/login', data={'email': email, 'senha': senha}, follow_redirects=True
    )


from bs4 import BeautifulSoup


def test_preview_evento_button_present(client, app):
    login(client, 'cli@test', '123')
    resp = client.get('/dashboard_cliente')
    assert resp.status_code == 200

    soup = BeautifulSoup(resp.data, 'html.parser')
    preview_btn = soup.select_one('#previewEventoBtn')
    assert preview_btn is not None

    evento_select = soup.select_one('#selectConfigEvento')
    assert evento_select is not None
    first_event_id = None
    for option in evento_select.find_all('option'):
        value = option.get('value')
        if value:
            first_event_id = value
            break

    assert first_event_id is not None

    expected_url = preview_btn['data-base-url'] + str(first_event_id)
    assert expected_url.endswith(str(first_event_id))

    preview_resp = client.get(expected_url)
    assert preview_resp.status_code in (200, 302)
