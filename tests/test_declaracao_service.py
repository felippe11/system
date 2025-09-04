import os
from pathlib import Path
from datetime import datetime

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'y')
os.environ.setdefault('DB_PASS', 'test')

import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models.user import Usuario, Cliente
from models import Evento
from models.certificado import DeclaracaoTemplate
from services import declaracao_service


@pytest.fixture
def app(tmp_path):
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.static_folder = tmp_path.as_posix()
    with app.app_context():
        db.create_all()
    yield app


def fake_import_weasyprint():
    class HTML:
        def __init__(self, string=None):
            self.string = string

        def write_pdf(self, path):
            with open(path, 'wb') as file:
                file.write(b'%PDF-1.4\n')

    class CSS:
        pass

    return HTML, CSS


def create_basic_entities():
    cliente = Cliente(
        nome='Cli',
        email='cli@example.com',
        senha=generate_password_hash('123', method='pbkdf2:sha256'),
    )
    db.session.add(cliente)
    db.session.commit()
    evento = Evento(
        cliente_id=cliente.id,
        nome='Evento',
        data_inicio=datetime.now(),
    )
    db.session.add(evento)
    usuario = Usuario(
        nome='User',
        cpf='1',
        email='user@example.com',
        senha=generate_password_hash('123', method='pbkdf2:sha256'),
        formacao='x',
        cliente_id=cliente.id,
    )
    db.session.add(usuario)
    db.session.commit()
    return cliente, evento, usuario


def test_gerar_declaracao_individual_padrao(app, monkeypatch):
    with app.app_context():
        cliente, evento, usuario = create_basic_entities()
        monkeypatch.setattr(
            declaracao_service,
            '_import_weasyprint',
            fake_import_weasyprint,
        )
        path = declaracao_service.gerar_declaracao_participacao(
            usuario.id, evento.id
        )
        assert path is not None
        full = Path(app.static_folder) / path
        assert full.exists()
        template = DeclaracaoTemplate.query.filter_by(
            cliente_id=cliente.id, tipo='individual'
        ).first()
        assert template is not None


def test_gerar_declaracao_coletiva_padrao(app, monkeypatch):
    with app.app_context():
        cliente, evento, usuario1 = create_basic_entities()
        usuario2 = Usuario(
            nome='User2',
            cpf='2',
            email='user2@example.com',
            senha=generate_password_hash('123', method='pbkdf2:sha256'),
            formacao='y',
            cliente_id=cliente.id,
        )
        db.session.add(usuario2)
        db.session.commit()
        monkeypatch.setattr(
            declaracao_service,
            '_import_weasyprint',
            fake_import_weasyprint,
        )
        path = declaracao_service.gerar_declaracao_coletiva(
            evento.id, [usuario1.id, usuario2.id]
        )
        assert path is not None
        full = Path(app.static_folder) / path
        assert full.exists()
        template = DeclaracaoTemplate.query.filter_by(
            cliente_id=cliente.id, tipo='coletiva'
        ).first()
        assert template is not None
