import os

import pytest

from config import Config
from app import create_app
from extensions import db
from models.user import Cliente
from models.material import Polo, Material

os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('DB_PASS', 'test')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options(
        app.config['SQLALCHEMY_DATABASE_URI']
    )
    with app.app_context():
        # Allow null "ativo" to simulate legacy data
        Material.__table__.columns['ativo'].nullable = True
        db.create_all()

        cliente = Cliente(nome='Cliente', email='c@test', senha='x')
        db.session.add(cliente)
        db.session.commit()

        polo = Polo(nome='Polo', cliente_id=cliente.id, ativo=True)
        db.session.add(polo)
        db.session.commit()

    yield app


@pytest.fixture
def session(app):
    with app.app_context():
        yield db.session


def test_filter_considers_null_as_active(session):
    cliente = Cliente.query.first()
    polo = Polo.query.first()

    ativo = Material(
        nome='Ativo',
        polo_id=polo.id,
        cliente_id=cliente.id,
        quantidade_inicial=0,
        quantidade_atual=0,
        quantidade_consumida=0,
        quantidade_minima=0,
        ativo=True,
    )
    inativo = Material(
        nome='Inativo',
        polo_id=polo.id,
        cliente_id=cliente.id,
        quantidade_inicial=0,
        quantidade_atual=0,
        quantidade_consumida=0,
        quantidade_minima=0,
        ativo=False,
    )
    nulo = Material(
        nome='Nulo',
        polo_id=polo.id,
        cliente_id=cliente.id,
        quantidade_inicial=0,
        quantidade_atual=0,
        quantidade_consumida=0,
        quantidade_minima=0,
        ativo=None,
    )
    session.add_all([ativo, inativo, nulo])
    session.commit()

    materiais = Material.query.filter(Material.ativo.isnot(False)).all()
    nomes = [m.nome for m in materiais]
    assert 'Ativo' in nomes
    assert 'Nulo' in nomes
    assert 'Inativo' not in nomes
