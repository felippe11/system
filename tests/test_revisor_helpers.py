import os
from datetime import date

import pytest
from flask import Flask, request

from extensions import db

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "y")
os.environ.setdefault("DB_PASS", "test")
from config import Config
from models import Evento, Formulario
from models.user import Cliente
from models.review import RevisorProcess
from utils.revisor_helpers import (
    parse_revisor_form,
    recreate_stages,
    update_process_eventos,
    update_revisor_process,
)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_ENGINE_OPTIONS=Config.build_engine_options("sqlite://"),
    )
    db.init_app(app)
    with app.app_context():
        db.create_all()
    yield app


def _create_cliente_formulario():
    cliente = Cliente(nome="Cli", email="cli@test", senha="x")
    db.session.add(cliente)
    db.session.commit()
    form = Formulario(nome="Form", cliente_id=cliente.id)
    db.session.add(form)
    db.session.commit()
    return cliente, form


def test_parse_revisor_form(app):
    with app.test_request_context(
        method="POST",
        data={
            "nome": "Processo A",
            "descricao": "Desc",
            "status": "Aberto",
            "formulario_id": 1,
            "nome": "Proc",
            "descricao": "Desc",
            "status": "ativo",
            "num_etapas": 2,
            "stage_name": ["Etapa 1", "Etapa 2"],
            "availability_start": "2024-01-10",
            "availability_end": "2024-01-20",

            "exibir_para_participantes": "on",
            "eventos_ids": [1, 2],

        },
    ):
        dados = parse_revisor_form(request)
    assert dados["nome"] == "Processo A"
    assert dados["descricao"] == "Desc"
    assert dados["status"] == "Aberto"
    assert dados["formulario_id"] == 1
    assert dados["nome"] == "Proc"
    assert dados["descricao"] == "Desc"
    assert dados["status"] == "ativo"
    assert dados["num_etapas"] == 2
    assert dados["stage_names"] == ["Etapa 1", "Etapa 2"]
    assert dados["availability_start"].date() == date(2024, 1, 10)
    assert dados["availability_end"].date() == date(2024, 1, 20)
    assert dados["exibir_para_participantes"] is True
    assert dados["eventos_ids"] == [1, 2]


def test_parse_revisor_form_no_eventos(app):
    with app.test_request_context(
        method="POST",
        data={"num_etapas": 1, "stage_name": ["Etapa"]},
    ):
        dados = parse_revisor_form(request)
    assert dados["eventos_ids"] == []


def test_parse_revisor_form_missing_stage(app):
    with app.test_request_context(
        method="POST",
        data={
            "num_etapas": 2,
            "stage_name": ["Etapa 1"],
            "nome": "Proc",
            "status": "ativo",
        },
    ):
        with pytest.raises(ValueError):
            parse_revisor_form(request)


def test_parse_revisor_form_missing_nome(app):
    with app.test_request_context(
        method="POST", data={"status": "Aberto", "num_etapas": 1, "stage_name": ["E1"]}
    ):
        with pytest.raises(ValueError):
            parse_revisor_form(request)


def test_parse_revisor_form_without_formulario_id(app):
    with app.test_request_context(
        method="POST",

        data={
            "num_etapas": 1,
            "stage_name": ["Etapa 1"],
            "nome": "Proc",
            "status": "ativo",
        },

    ):
        dados = parse_revisor_form(request)
    assert dados["formulario_id"] is None

def test_update_and_recreate_stages(app):
    with app.app_context():
        cliente, form = _create_cliente_formulario()
        processo = RevisorProcess(
            cliente_id=cliente.id,
            nome="Proc",
            status="ativo",
        )
        db.session.add(processo)
        db.session.commit()

        with app.test_request_context(
            method="POST",
            data={
                "nome": "Proc",
                "status": "Aberto",
                "formulario_id": form.id,
                "nome": "Proc",
                "status": "ativo",
                "num_etapas": 2,
                "stage_name": ["E1", "E2"],
                "exibir_para_participantes": "on",
            },
        ):
            dados = parse_revisor_form(request)
        update_revisor_process(processo, dados)
        recreate_stages(processo, dados["stage_names"])
        db.session.refresh(processo)
        assert processo.num_etapas == 2
        assert [e.nome for e in processo.etapas] == ["E1", "E2"]

        with app.test_request_context(
            method="POST",
            data={
                "nome": "Proc",
                "status": "Aberto",
                "formulario_id": form.id,
                "nome": "Proc",
                "status": "ativo",
                "num_etapas": 1,
                "stage_name": ["Novo"],
            },
        ):
            dados2 = parse_revisor_form(request)
        update_revisor_process(processo, dados2)
        recreate_stages(processo, dados2["stage_names"])
        db.session.refresh(processo)
        assert processo.num_etapas == 1
        assert [e.nome for e in processo.etapas] == ["Novo"]


def test_update_process_eventos(app):
    with app.app_context():
        cliente, form = _create_cliente_formulario()
        e1 = Evento(cliente_id=cliente.id, nome="E1", inscricao_gratuita=True, publico=True)
        e2 = Evento(cliente_id=cliente.id, nome="E2", inscricao_gratuita=True, publico=True)
        db.session.add_all([e1, e2])
        db.session.commit()
        processo = RevisorProcess(
            cliente_id=cliente.id,
            nome="Proc",
            status="ativo",
        )
        db.session.add(processo)
        db.session.commit()

        update_process_eventos(processo, [e1.id])
        db.session.refresh(processo)
        assert [e.id for e in processo.eventos] == [e1.id]

        update_process_eventos(processo, [e2.id])
        db.session.refresh(processo)
        assert [e.id for e in processo.eventos] == [e2.id]


def test_update_process_eventos_none(app):
    with app.app_context():
        cliente, _ = _create_cliente_formulario()
        processo = RevisorProcess(cliente_id=cliente.id)
        db.session.add(processo)
        db.session.commit()

        update_process_eventos(processo, None)
        db.session.refresh(processo)
        assert processo.eventos == []
