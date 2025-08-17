import os
import sys
import types
from io import BytesIO
from unittest.mock import patch

import pytest
from werkzeug.security import generate_password_hash

from config import Config
from app import create_app
from extensions import db
from models import Evento
from models.user import Usuario, Cliente

# Configure in-memory database
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)


@pytest.fixture
def app():
    os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
    os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
    sys.modules.pop('services.relatorio_service', None)
    sys.modules['transformers'] = types.SimpleNamespace(pipeline=lambda *a, **k: lambda *a2, **k2: None)
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123'))
        admin = Usuario(nome='Admin', cpf='1', email='admin@test', senha=generate_password_hash('123'), formacao='x', tipo='admin')
        db.session.add_all([cliente, admin])
        db.session.commit()
        evento = Evento(cliente_id=cliente.id, nome='Evento')
        db.session.add(evento)
        db.session.commit()
    yield app
    sys.modules.pop('transformers', None)


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post('/login', data={'email': 'admin@test', 'senha': '123'}, follow_redirects=True)


def test_gerar_relatorio_evento_preview(client, app):
    login(client)
    with app.app_context():
        evento = Evento.query.first()
    pdf_bytes = b'%PDF-1.4'
    with patch('routes.relatorio_pdf_routes.gerar_texto_relatorio', return_value='TXT'), \
         patch('routes.relatorio_pdf_routes.criar_documento_word', return_value=BytesIO(b'DOC')), \
         patch('routes.relatorio_pdf_routes.converter_para_pdf', return_value=BytesIO(pdf_bytes)):
        resp = client.post(f'/gerar_relatorio_evento/{evento.id}?preview=1', json={'dados': []})
    assert resp.status_code == 200
    assert resp.mimetype == 'application/pdf'
    assert resp.data.startswith(pdf_bytes)
