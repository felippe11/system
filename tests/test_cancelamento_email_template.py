import os
import flask
from flask import Flask
from datetime import datetime, date, time
from types import SimpleNamespace

os.environ.setdefault("GOOGLE_CLIENT_ID", "test")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test")

from routes import agendamento_routes


def test_enviar_email_cancelamento_uses_template(monkeypatch):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    app = Flask(__name__, template_folder=os.path.join(base_dir, "templates"))

    professor = SimpleNamespace(nome="Prof", email="prof@example.com")
    evento = SimpleNamespace(
        nome="Evento",
        local="Local",
        cliente=SimpleNamespace(nome="Cliente"),
        configuracoes_agendamento=[],
    )
    horario = SimpleNamespace(
        data=date.today(),
        horario_inicio=time(10, 0),
        horario_fim=time(11, 0),
        evento=evento,
    )
    agendamento = SimpleNamespace(
        id=1,
        professor=professor,
        horario=horario,
        evento=evento,
        escola_nome="Escola",
        turma="Turma",
        quantidade_alunos=30,
        data_cancelamento=datetime.now(),
    )

    called = {"sent": False}

    def fake_async(*args, **kwargs):
        called["sent"] = True

    monkeypatch.setattr(
        agendamento_routes.NotificacaoAgendamentoService,
        "_enviar_email_async",
        fake_async,
    )

    class DummyThread:
        def __init__(self, target, args):
            self.target = target
            self.args = args

        def start(self):
            self.target(*self.args)

    monkeypatch.setattr(agendamento_routes.threading, "Thread", DummyThread)

    monkeypatch.setattr(flask, "url_for", lambda *args, **kwargs: "http://example.com")
    app.jinja_env.globals["url_for"] = flask.url_for
    app.jinja_env.globals["now"] = lambda: datetime.now()

    with app.app_context():
        agendamento_routes.NotificacaoAgendamentoService.enviar_email_cancelamento(agendamento)

    assert called["sent"]
