import os
import tempfile
import types
from unittest.mock import patch
import pytest
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Oficina, Inscricao
from models.user import Usuario, Cliente

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cli', email='cli@test', senha=generate_password_hash('123'))
        admin = Usuario(nome='Admin', cpf='1', email='admin@test', senha=generate_password_hash('123'), formacao='x', tipo='admin')
        usuario = Usuario(nome='User', cpf='2', email='user@test', senha=generate_password_hash('123'), formacao='x')
        db.session.add_all([cliente, admin, usuario])
        db.session.commit()
        oficina = Oficina(titulo='Of', descricao='desc', ministrante_id=None, vagas=10, carga_horaria='8', estado='SP', cidade='SP', cliente_id=cliente.id)
        db.session.add(oficina)
        db.session.commit()
        inscricao = Inscricao(usuario_id=usuario.id, cliente_id=cliente.id, oficina_id=oficina.id, status_pagamento='approved')
        db.session.add(inscricao)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_gerar_certificado_individual_admin_get(client, app):
    with app.app_context():
        oficina = Oficina.query.first()
        usuario = Usuario.query.filter_by(email='user@test').first()
        path = f'static/certificados/certificado_{usuario.id}_{oficina.id}.pdf'

    def fake(oficina, inscritos, pdf_path):
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        with open(pdf_path, 'wb') as f:
            f.write(b'PDF')

    with patch('routes.pdf_routes.gerar_certificados_pdf', side_effect=fake):
        login(client, 'admin@test', '123')
        resp = client.get(f'/gerar_certificado_individual_admin?oficina_id={oficina.id}&usuario_id={usuario.id}')
        assert resp.status_code == 200
        assert resp.mimetype == 'application/pdf'
        assert os.path.exists(path)
        os.remove(path)
