import os
import pytest
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from config import Config

os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db

    Usuario,
    Cliente,
    Evento,
    EventoInscricaoTipo,
    Pagamento,
    PasswordResetToken,
    usuario_clientes,
    ConfiguracaoEvento,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'

    with app.app_context():
        db.create_all()
        admin = Usuario(
            nome='Admin', cpf='1', email='admin@example.com',
            senha=generate_password_hash('123'), formacao='x', tipo='admin'
        )
        db.session.add(admin)
        cliente = Cliente(
            nome='Cli', email='cli@example.com', senha=generate_password_hash('456')
        )
        db.session.add(cliente)
        db.session.commit()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def _assoc_count(app, cliente_id):
    with app.app_context():
        return db.session.execute(
            db.select(db.func.count()).select_from(usuario_clientes).where(
                usuario_clientes.c.cliente_id == cliente_id
            )
        ).scalar()


def _setup_event_with_payment(app, cliente):
    with app.app_context():
        evento = Evento(cliente_id=cliente.id, nome='EV', habilitar_lotes=False, inscricao_gratuita=False)
        db.session.add(evento)
        db.session.commit()
        
        tipo = EventoInscricaoTipo(evento_id=evento.id, nome='P', preco=10.0)
        db.session.add(tipo)
        usuario = Usuario(
            nome='Part', cpf='2', email='p@example.com',
            senha=generate_password_hash('123'), formacao='x', tipo='participante',
            cliente_id=cliente.id
        )
        db.session.add(usuario)
        db.session.commit()

        pagamento = Pagamento(usuario_id=usuario.id, evento_id=evento.id, tipo_inscricao_id=tipo.id)
        db.session.add(pagamento)
        db.session.commit()
        return evento.id


def _setup_event_with_config(app, cliente):
    with app.app_context():
        evento = Evento(cliente_id=cliente.id, nome='EV_CFG')
        db.session.add(evento)
        db.session.commit()

        cfg = ConfiguracaoEvento(evento_id=evento.id, cliente_id=cliente.id)
        db.session.add(cfg)
        db.session.commit()
        return evento.id


def test_excluir_evento_remove_pagamentos(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        evento_id = _setup_event_with_payment(app, cliente)

    login(client, 'admin@example.com', '123')
    resp = client.post(f'/excluir_evento/{evento_id}', follow_redirects=True)
    assert resp.status_code in (200, 302)

    with app.app_context():
        assert Pagamento.query.count() == 0
        assert Evento.query.get(evento_id) is None


def test_excluir_cliente_remove_pagamentos(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        evento_id = _setup_event_with_payment(app, cliente)
        cid = cliente.id

    login(client, 'admin@example.com', '123')
    resp = client.post(f'/excluir_cliente/{cid}', follow_redirects=True)
    assert resp.status_code in (200, 302)

    with app.app_context():
        assert Cliente.query.get(cid) is None
        assert Evento.query.filter_by(cliente_id=cid).count() == 0
        assert Pagamento.query.count() == 0


def test_excluir_cliente_cleans_association(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        user = Usuario(
            nome='User', cpf='99', email='u@example.com',
            senha=generate_password_hash('123'), formacao='x', tipo='participante'
        )
        db.session.add(user)
        db.session.commit()
        db.session.execute(
            usuario_clientes.insert().values(usuario_id=user.id, cliente_id=cliente.id)
        )
        db.session.commit()
        cid = cliente.id
        assert _assoc_count(app, cid) == 1

    login(client, 'admin@example.com', '123')
    resp = client.post(f'/excluir_cliente/{cid}', follow_redirects=True)
    assert resp.status_code in (200, 302)

    with app.app_context():
        assert _assoc_count(app, cid) == 0
        assert Cliente.query.get(cid) is None


def test_excluir_evento_remove_config(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        evento_id = _setup_event_with_config(app, cliente)

    login(client, 'admin@example.com', '123')
    resp = client.post(f'/excluir_evento/{evento_id}', follow_redirects=True)
    assert resp.status_code in (200, 302)

    with app.app_context():
        assert ConfiguracaoEvento.query.filter_by(evento_id=evento_id).count() == 0


def test_excluir_cliente_removes_event_config(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        evento_id = _setup_event_with_config(app, cliente)
        cid = cliente.id

    login(client, 'admin@example.com', '123')
    resp = client.post(f'/excluir_cliente/{cid}', follow_redirects=True)
    assert resp.status_code in (200, 302)

    with app.app_context():
        assert ConfiguracaoEvento.query.count() == 0
        assert Evento.query.filter_by(cliente_id=cid).count() == 0


def test_excluir_cliente_remove_reset_tokens(client, app):
    with app.app_context():
        cliente = Cliente.query.first()
        user = Usuario(
            nome="ResetUser",
            cpf="3",
            email="reset@example.com",
            senha=generate_password_hash("123"),
            formacao="x",
            tipo="participante",
            cliente_id=cliente.id,
        )
        db.session.add(user)
        db.session.commit()
        token = PasswordResetToken(
            usuario_id=user.id,
            token="tok",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.session.add(token)
        db.session.commit()
        cid = cliente.id
        assert PasswordResetToken.query.count() == 1

    login(client, "admin@example.com", "123")
    resp = client.post(f"/excluir_cliente/{cid}", follow_redirects=True)
    assert resp.status_code in (200, 302)

    with app.app_context():
        assert PasswordResetToken.query.count() == 0
        assert Usuario.query.filter_by(cliente_id=cid).count() == 0

