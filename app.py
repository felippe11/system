from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Message
from flask_cors import CORS
from flask_socketio import join_room
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from config import Config
from extensions import db, login_manager, migrate, mail, socketio
from models import Usuario, Cliente, Ministrante, Inscricao
from utils import brasilia_filter
import logging
import os
import pytz

from services.mp_service import get_sdk


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.jinja_env.add_extension('jinja2.ext.do')
    app.config["UPLOAD_FOLDER"] = "uploads"

    # Inicialização de extensões
    socketio.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    CORS(app)

    login_manager.login_view = "auth_routes.login"
    login_manager.session_protection = "strong"

    # Filtros Jinja2
    @app.template_filter('string_to_date')
    def string_to_date(value):
        try:
            return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
        except (ValueError, TypeError):
            return value

    @app.template_filter('brasilia')
    def brasilia_filter(dt):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.utc)
        dt_brasilia = dt.astimezone(pytz.timezone("America/Sao_Paulo"))
        return dt_brasilia.strftime("%d/%m/%Y %H:%M:%S")

    # Registro de rotas
    from routes import register_routes
    register_routes(app)

    with app.app_context():
        db.create_all()

    return app


# Inicialização do app
app = create_app()


# Função para reconciliar pagamentos pendentes
def reconciliar_pendentes():
    sdk = get_sdk()
    if not sdk:
        return
    ontem = datetime.utcnow() - timedelta(hours=24)
    pendentes = Inscricao.query.filter(
        Inscricao.status_pagamento == "pending",
        Inscricao.created_at < ontem
    ).all()

    for ins in pendentes:
        resp = sdk.payment().get(ins.payment_id)
        if resp["response"]["status"] == "approved":
            ins.status_pagamento = "approved"
            db.session.commit()


# Agendamento do reconciliador
scheduler = BackgroundScheduler()
scheduler.add_job(reconciliar_pendentes, "cron", hour=3, minute=0)
scheduler.start()


# Socket.IO para check-ins
@socketio.on('join', namespace='/checkins')
def on_join(data):
    sala = data.get('sala')
    if sala:
        join_room(sala)


# Rota básica
@app.route("/")
def index():
    now = datetime.utcnow()
    return f"Horário de Brasília: {brasilia_filter(now)}"

# Execução da aplicação
if __name__ == '__main__':
    socketio.run(app, debug=True)
