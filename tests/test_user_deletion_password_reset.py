import os
import pytest
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from config import Config

os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models import PasswordResetToken  # noqa: E402
from models.user import Usuario


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        admin = Usuario(
            nome='Admin', cpf='admin', email='admin@test',
            senha=generate_password_hash('123'), formacao='F', tipo='admin'
        )
        participante = Usuario(
            nome='User', cpf='123', email='user@test',
            senha=generate_password_hash('123'), formacao='F', tipo='participante'
        )
        db.session.add_all([admin, participante])
        db.session.commit()
        token = PasswordResetToken(
            usuario_id=participante.id,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(token)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def test_delete_participant_removes_password_tokens(client, app):
    login(client, 'admin@test', '123')
    with app.app_context():
        user = Usuario.query.filter_by(cpf='123').first()
        assert PasswordResetToken.query.filter_by(usuario_id=user.id).count() == 1
        uid = user.id

    resp = client.post(f'/excluir_participante/{uid}', follow_redirects=True)
    assert resp.status_code in (200, 302)

    with app.app_context():
        assert Usuario.query.get(uid) is None
        assert PasswordResetToken.query.filter_by(usuario_id=uid).count() == 0
