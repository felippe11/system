import io
import pytest
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['LOGIN_DISABLED'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def test_upload_and_download_binary(client):
    data = {'file': (io.BytesIO(b'\x01\x02\x03'), 'dados.bin')}
    resp = client.post('/api/binarios', data=data, content_type='multipart/form-data')
    assert resp.status_code == 201
    arquivo_id = resp.get_json()['id']
    resp = client.get(f'/api/binarios/{arquivo_id}')
    assert resp.status_code == 200
    assert resp.data == b'\x01\x02\x03'
