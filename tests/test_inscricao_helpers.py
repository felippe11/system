import os
import pytest

os.environ["SECRET_KEY"] = "testing"
from config import Config

Config.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from flask import Flask
from extensions import db
from werkzeug.security import generate_password_hash
from models import (
    Evento,
    Cliente,
    LinkCadastro,
    Usuario,
    Inscricao,
)
from routes.inscricao_routes import (
    _resolver_link_evento,
    _criar_usuario_e_inscricao,
    SenhaIncorretaError,
    InscricaoExistenteError,
)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.SQLALCHEMY_ENGINE_OPTIONS
    db.init_app(app)

    with app.app_context():
        db.create_all()
        cliente = Cliente(nome='Cliente', email='c@example.com', senha='123')
        db.session.add(cliente)
        db.session.commit()

        evento = Evento(
            cliente_id=cliente.id,
            nome='Evento',
            habilitar_lotes=False,
            inscricao_gratuita=True,
            publico=True,
            status='ativo',
            requer_aprovacao=False,
        )
        db.session.add(evento)
        db.session.commit()

        link = LinkCadastro(cliente_id=cliente.id, evento_id=evento.id, token='abc')
        db.session.add(link)
        db.session.commit()

    yield app


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield


def test_resolver_link_evento(app_ctx):
    link, evento, cliente_id = _resolver_link_evento('abc')
    assert link is not None
    assert evento is not None
    assert cliente_id == evento.cliente_id

    with pytest.raises(ValueError):
        _resolver_link_evento('invalid')


def test_criar_usuario_e_inscricao(app_ctx):
    evento = Evento.query.first()
    usuario, inscricao, duplicado = _criar_usuario_e_inscricao(
        nome='Alice',
        cpf='111',
        email='alice@example.com',
        senha='123',
        formacao='Formacao',
        estados=['SP'],
        cidades=['Sao Paulo'],
        lote_id=None,
        lote_tipo_id=None,
        tipo_insc_id=None,
        cliente_id=evento.cliente_id,
        evento=evento,
        form={},
    )
    assert usuario.id is not None
    assert inscricao.usuario_id == usuario.id
    assert duplicado is False


def test_criar_usuario_e_inscricao_errors(app_ctx):
    evento = Evento.query.first()
    user = Usuario(
        nome='Bob',
        cpf='222',
        email='bob@example.com',
        senha=generate_password_hash('secret', method="pbkdf2:sha256"),
        formacao='F',
    )
    db.session.add(user)
    db.session.commit()

    with pytest.raises(SenhaIncorretaError):
        _criar_usuario_e_inscricao(
            nome='Bob',
            cpf='222',
            email='bob@example.com',
            senha='wrong',
            formacao='F',
            estados=[],
            cidades=[],
            lote_id=None,
            lote_tipo_id=None,
            tipo_insc_id=None,
            cliente_id=evento.cliente_id,
            evento=evento,
            form={},
        )

    # existing inscription
    inscr = Inscricao(
        usuario_id=user.id,
        evento_id=evento.id,
        cliente_id=evento.cliente_id,
    )
    db.session.add(inscr)
    db.session.commit()

    with pytest.raises(InscricaoExistenteError):
        _criar_usuario_e_inscricao(
            nome='Bob',
            cpf='222',
            email='bob@example.com',
            senha='secret',
            formacao='F',
            estados=[],
            cidades=[],
            lote_id=None,
            lote_tipo_id=None,
            tipo_insc_id=None,
            cliente_id=evento.cliente_id,
            evento=evento,
            form={},
        )
