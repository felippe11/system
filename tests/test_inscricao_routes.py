import pytest
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app
from extensions import db
from models import Evento, EventoInscricaoTipo, LoteInscricao, LoteTipoInscricao
from models.user import Cliente, LinkCadastro

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()

        cliente = Cliente(nome='Cliente', email='c@example.com', senha='123')
        db.session.add(cliente)
        db.session.commit()

        evento = Evento(cliente_id=cliente.id, nome='Evento Teste', habilitar_lotes=True, inscricao_gratuita=False)
        db.session.add(evento)
        db.session.commit()

        tipo = EventoInscricaoTipo(evento_id=evento.id, nome='Pago', preco=20.0)
        db.session.add(tipo)
        db.session.commit()

        lote = LoteInscricao(evento_id=evento.id, nome='Lote 1')
        db.session.add(lote)
        db.session.commit()

        lt = LoteTipoInscricao(lote_id=lote.id, tipo_inscricao_id=tipo.id, preco=20.0)
        db.session.add(lt)
        db.session.commit()

        link = LinkCadastro(
            cliente_id=cliente.id,
            evento_id=evento.id,
            token='testtoken',
            slug_customizado='test-slug'
        )
        db.session.add(link)
        db.session.commit()

        # Evento sem link de cadastro
        evento2 = Evento(cliente_id=cliente.id, nome='Evento Sem Link', habilitar_lotes=False, inscricao_gratuita=True)
        db.session.add(evento2)
        db.session.commit()

    yield app

@pytest.fixture

def client(app):
    return app.test_client()

def test_get_inscricao_page(client):
    resp = client.get('/inscricao/token/testtoken')
    assert resp.status_code == 200
    assert b'Evento Teste' in resp.data


def test_get_inscricao_page_slug(client):
    resp = client.get('/inscricao/test-slug', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Evento Teste' in resp.data


def test_inscricao_por_id(client, app):
    with app.app_context():
        evento = Evento.query.filter_by(nome='Evento Sem Link').first()
        assert evento is not None
        evento_id = evento.id

    resp = client.get(f'/inscricao/{evento_id}')
    assert resp.status_code == 200
    assert b'Evento Sem Link' in resp.data


def test_inscricao_evento_route_redirect(client, app):
    with app.app_context():
        evento = Evento.query.filter_by(nome='Evento Sem Link').first()
        evento_id = evento.id

    resp = client.get(f'/evento/{evento_id}/inscricao', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Evento Sem Link' in resp.data


def test_render_multiple_tipos_no_lote(client, app):
    """Should display all tipos with their respective lote prices."""
    with app.app_context():
        cliente = Cliente.query.first()
        evento = Evento(
            cliente_id=cliente.id,
            nome='Evento Multi',
            habilitar_lotes=True,
            inscricao_gratuita=False,
        )
        db.session.add(evento)
        db.session.commit()

        tipo1 = EventoInscricaoTipo(evento_id=evento.id, nome='Tipo 1', preco=10.0)
        tipo2 = EventoInscricaoTipo(evento_id=evento.id, nome='Tipo 2', preco=15.0)
        db.session.add_all([tipo1, tipo2])
        db.session.commit()

        lote = LoteInscricao(evento_id=evento.id, nome='Lote Multi', ativo=True)
        db.session.add(lote)
        db.session.commit()

        lt1 = LoteTipoInscricao(lote_id=lote.id, tipo_inscricao_id=tipo1.id, preco=11.0)
        lt2 = LoteTipoInscricao(lote_id=lote.id, tipo_inscricao_id=tipo2.id, preco=16.0)
        db.session.add_all([lt1, lt2])
        db.session.commit()

        link = LinkCadastro(cliente_id=cliente.id, evento_id=evento.id, token='multitoken')
        db.session.add(link)
        db.session.commit()

    resp = client.get('/inscricao/multitoken')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'Tipo 1' in html and 'Tipo 2' in html
    assert 'R$ 11.0' in html and 'R$ 16.0' in html


def test_inscricao_sanitizes_input(client, app):
    data = {
        'nome': '<b>Alice</b>',
        'cpf': '111',
        'email': 'alice@example.com',
        'senha': '123',
        'formacao': '<script>hack</script>',
        'estados[]': ['<i>SP</i>'],
        'cidades[]': ['<i>Sao Paulo</i>'],
        'lote_id': '',
        'lote_tipo_inscricao_id': '',
        'tipo_inscricao_id': ''
    }
    resp = client.post('/inscricao/token/testtoken', data=data, follow_redirects=True)
    assert resp.status_code in (200, 302)
    with app.app_context():
        from models import Usuario
        user = Usuario.query.filter_by(email='alice@example.com').first()
        assert user is not None
        assert user.nome == 'Alice'
        assert user.formacao == 'hack'
        assert '<' not in (user.estados or '')
        assert '<' not in (user.cidades or '')

