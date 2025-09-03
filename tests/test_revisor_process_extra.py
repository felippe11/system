import os
from datetime import date, timedelta
import pytest
from werkzeug.security import generate_password_hash
from config import Config
from jinja2 import ChoiceLoader, DictLoader
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from flask import Flask
from extensions import db, login_manager, migrate
from flask_migrate import upgrade

from models import Formulario, Evento
from models.user import Cliente
from models.review import RevisorProcess
from routes.revisor_routes import revisor_routes

@pytest.fixture
def app():
    templates_path = os.path.join(os.path.dirname(__file__), '..', 'templates')
    app = Flask(__name__, template_folder=templates_path)
    app.jinja_loader = ChoiceLoader([
        DictLoader({'base.html': '{% block content %}{% endblock %}'}),
        app.jinja_loader,
    ])
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.build_engine_options('sqlite://')
    app.jinja_env.globals['csrf_token'] = lambda: ''
    login_manager.init_app(app)
    @login_manager.user_loader
    def load_user(user_id):
        return Cliente.query.get(int(user_id))
    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(revisor_routes)
    with app.app_context():
        try:
            upgrade(revision="heads")
        except SystemExit:
            db.create_all()
        c1 = Cliente(nome='C1', email='c1@test', senha=generate_password_hash('123', method="pbkdf2:sha256"))
        c2 = Cliente(nome='C2', email='c2@test', senha=generate_password_hash('123', method="pbkdf2:sha256"))
        db.session.add_all([c1, c2])
        db.session.commit()
        f1 = Formulario(nome='F1', cliente_id=c1.id)
        f2 = Formulario(nome='F2', cliente_id=c2.id)
        db.session.add_all([f1, f2])
        db.session.commit()
        e1 = Evento(
            cliente_id=c1.id,
            nome='E1',
            inscricao_gratuita=True,
            publico=True,
            status='ativo',
        )
        e2 = Evento(
            cliente_id=c2.id,
            nome='E2',
            inscricao_gratuita=True,
            publico=True,
            status='ativo',
        )
        e3 = Evento(
            cliente_id=c2.id,
            nome='E3',
            inscricao_gratuita=True,
            publico=True,
            status='ativo',
        )
        db.session.add_all([e1, e2, e3])
        db.session.commit()

        e1.formularios.append(f1)
        e2.formularios.append(f2)
        e3.formularios.append(f2)
        db.session.commit()

        db.session.add(
            RevisorProcess(
                cliente_id=c1.id,
                formulario_id=f1.id,
                num_etapas=1,
                availability_start=date.today() - timedelta(days=1),
                availability_end=date.today() + timedelta(days=1),
                exibir_para_participantes=True,
                nome="Proc",
                status="ativo",
            )
        )

        proc1 = RevisorProcess(
            cliente_id=c1.id,
            formulario_id=f1.id,
            num_etapas=1,
            availability_start=date.today() - timedelta(days=1),
            availability_end=date.today() + timedelta(days=1),
            exibir_para_participantes=True,
            eventos=[e1],
            nome="Proc",
            status="ativo",
        )

        proc2 = RevisorProcess(
            cliente_id=c2.id,
            formulario_id=f2.id,
            num_etapas=1,
            availability_start=date.today() - timedelta(days=3),
            availability_end=date.today() - timedelta(days=1),
            exibir_para_participantes=True,
            eventos=[e2],
            nome="Proc",
            status="ativo",
        )
        proc3 = RevisorProcess(
            cliente_id=c1.id,
            formulario_id=f1.id,
            num_etapas=1,
            exibir_para_participantes=False,

            nome="Proc",
            status="ativo",

        )
        proc_inactive = RevisorProcess(
            cliente_id=c2.id,
            formulario_id=f2.id,
            num_etapas=1,
            availability_start=date.today() - timedelta(days=1),
            availability_end=date.today() + timedelta(days=1),
            exibir_para_participantes=True,
            status='finalizado',
            eventos=[e3],
        )
        db.session.add_all([proc1, proc2, proc3, proc_inactive])
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()


def test_process_creation_with_dates(app):
    with app.app_context():
        proc = RevisorProcess.query.filter_by(exibir_para_participantes=True).first()
        assert proc.exibir_para_participantes is True
        assert proc.availability_start is not None
        assert proc.availability_end is not None
        start = proc.availability_start.date() if hasattr(proc.availability_start, 'date') else proc.availability_start
        end = proc.availability_end.date() if hasattr(proc.availability_end, 'date') else proc.availability_end
        assert start <= date.today() <= end



def test_visibility_flag_filters(app):
    with app.app_context():
        visible = (
            RevisorProcess.query
            .filter(
                RevisorProcess.exibir_para_participantes.is_(True),
                RevisorProcess.eventos.any(),
                RevisorProcess.status == 'ativo',
            )
            .all()
        )
        hidden = (
            RevisorProcess.query
            .filter(
                RevisorProcess.exibir_para_participantes.is_(False),
                RevisorProcess.eventos.any(),
            )
            .all()
        )
        assert len(visible) == 2
        assert len(hidden) == 0


def test_eligible_events_route(client, app):
    resp = client.get('/revisor/eligible_events')
    assert resp.status_code == 200
    data = resp.get_json()
    with app.app_context():
        e1 = Evento.query.filter_by(nome='E1').first()
        e3 = Evento.query.filter_by(nome='E3').first()
    assert data == [{'id': e1.id, 'nome': 'E1'}]
    assert {'id': e3.id, 'nome': 'E3'} not in data


def test_select_event_route(client):
    resp = client.get('/processo_seletivo')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'E1' in html
    assert 'E2' not in html
    assert 'E3' not in html


def test_revisorprocess_eventos_relationship(app):
    with app.app_context():
        proc = RevisorProcess.query.filter(
            RevisorProcess.exibir_para_participantes.is_(True),
            RevisorProcess.eventos.any(),
        ).first()
        nomes = {e.nome for e in proc.eventos}
        assert nomes == {'E1'}


def test_process_events_are_active_and_public(app):
    with app.app_context():
        proc = RevisorProcess.query.filter(RevisorProcess.eventos.any()).first()
        evento = proc.eventos[0]
        assert evento.status == 'ativo'
        assert evento.publico is True

def test_config_route_saves_availability(client, app):
    with app.app_context():
        cliente = Cliente.query.filter_by(email='c1@test').first()
        formulario = Formulario.query.filter_by(cliente_id=cliente.id).first()
        start = date.today()
        end = start + timedelta(days=2)

        from flask_login import login_user, logout_user

        with client:
            with app.test_request_context():
                login_user(cliente)
            resp = client.post(
                '/revisor/processos',
                data={
                    'formulario_id': formulario.id,
                    'nome': 'Proc',
                    'status': 'ativo',
                    'num_etapas': 1,
                    'stage_name': ['Etapa 1'],
                    'availability_start': start.strftime('%Y-%m-%d'),
                    'availability_end': end.strftime('%Y-%m-%d'),
                    'exibir_para_participantes': 'on',
                },
            )
            with app.test_request_context():
                logout_user()

        assert resp.status_code == 201
        proc_id = resp.get_json()['id']
        proc = RevisorProcess.query.get(proc_id)
        assert proc.availability_start.date() == start
        assert proc.availability_end.date() == end


def test_config_route_saves_eventos(client, app):
    with app.app_context():
        cliente = Cliente.query.filter_by(email='c1@test').first()
        formulario = Formulario.query.filter_by(cliente_id=cliente.id).first()
        evento = Evento.query.filter_by(cliente_id=cliente.id).first()

        from flask_login import login_user, logout_user

        with client:
            with app.test_request_context():
                login_user(cliente)
            resp = client.post(
                '/revisor/processos',
                data={
                    'formulario_id': formulario.id,
                    'nome': 'Proc',
                    'status': 'ativo',
                    'num_etapas': 1,
                    'stage_name': ['Etapa 1'],
                    'eventos_ids': [evento.id],
                },
            )
            with app.test_request_context():
                logout_user()

        assert resp.status_code == 201
        proc_id = resp.get_json()['id']
        proc = RevisorProcess.query.get(proc_id)
        assert [e.id for e in proc.eventos] == [evento.id]


def test_config_route_renders_eventos(client, app):
    with app.app_context():
        cliente = Cliente.query.filter_by(email='c1@test').first()
        evento = Evento.query.filter_by(cliente_id=cliente.id).first()

        from flask_login import login_user, logout_user

        with client:
            with app.test_request_context():
                login_user(cliente)
            proc = (
                RevisorProcess.query.filter_by(cliente_id=cliente.id)
                .filter(RevisorProcess.eventos.any())
                .all()[0]
            )
            resp = client.get(f'/revisor/processos/{proc.id}')
            with app.test_request_context():
                logout_user()

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert evento.nome in html
    assert f'value="{evento.id}" selected' in html
    assert 'E2' not in html

