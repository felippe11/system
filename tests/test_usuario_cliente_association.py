import pytest
from werkzeug.security import generate_password_hash
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models import Evento, Inscricao
from models.user import Cliente, Usuario, LinkCadastro, usuario_clientes

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    with app.app_context():
        db.create_all()
        admin = Usuario(nome='Admin', cpf='0', email='admin@test', senha=generate_password_hash('123'), formacao='X', tipo='admin')
        c1 = Cliente(nome='C1', email='c1@test', senha=generate_password_hash('123'))
        c2 = Cliente(nome='C2', email='c2@test', senha=generate_password_hash('123'))
        db.session.add_all([admin, c1, c2])
        db.session.commit()
        e1 = Evento(cliente_id=c1.id, nome='E1', habilitar_lotes=False, inscricao_gratuita=True)
        e2 = Evento(cliente_id=c2.id, nome='E2', habilitar_lotes=False, inscricao_gratuita=True)
        db.session.add_all([e1, e2])
        db.session.commit()
        link1 = LinkCadastro(cliente_id=c1.id, evento_id=e1.id, token='t1')
        link2 = LinkCadastro(cliente_id=c2.id, evento_id=e2.id, token='t2')
        db.session.add_all([link1, link2])
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post('/login', data={'email': email, 'senha': senha}, follow_redirects=True)


def _assoc_count(app, usuario_id, cliente_id):
    with app.app_context():
        res = db.session.execute(
            db.select(db.func.count()).select_from(usuario_clientes).where(
                usuario_clientes.c.usuario_id == usuario_id,
                usuario_clientes.c.cliente_id == cliente_id,
            )
        ).scalar()
        return res


def test_association_and_listing(client, app):
    data = {'nome': 'User', 'cpf': '111', 'email': 'user@test', 'senha': '123', 'formacao': 'F'}
    resp = client.post('/inscricao/token/t1', data=data, follow_redirects=True)
    assert resp.status_code in (200, 302)

    resp = client.post('/inscricao/token/t2', data=data, follow_redirects=True)
    assert resp.status_code in (200, 302)

    with app.app_context():
        user = Usuario.query.filter_by(email='user@test').first()
        c1 = Cliente.query.filter_by(nome='C1').first()
        c2 = Cliente.query.filter_by(nome='C2').first()
        assert _assoc_count(app, user.id, c1.id) == 1
        assert _assoc_count(app, user.id, c2.id) == 1

    login(client, 'admin@test', '123')
    resp1 = client.get(f'/listar_usuarios/{c1.id}')
    assert resp1.status_code == 200
    assert 'user@test' in resp1.get_data(as_text=True)

    resp2 = client.get(f'/listar_usuarios/{c2.id}')
    assert resp2.status_code == 200
    assert 'user@test' in resp2.get_data(as_text=True)
