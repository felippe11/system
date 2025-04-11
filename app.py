from flask import Flask
from config import Config
from extensions import db, login_manager, migrate, mail
from datetime import datetime
import os
import logging
import pytz
from models import Usuario, Cliente, Ministrante  # ou só os que você precisa
from extensions import socketio  # Importa a instância de SocketIO
from flask_socketio import join_room


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.jinja_env.add_extension('jinja2.ext.do')
    app.config["UPLOAD_FOLDER"] = "uploads" # Pasta para salvar os arquivos
    
    
    # Initialize o SocketIO com o app
    socketio.init_app(app)
    
    app.debug = True
    # Configuração de logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # Inicializar extensões
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)  # Já inicializa o migrate importado de extensions
    mail.init_app(app)
    
    # REMOVA ESTA LINHA - você já está inicializando o migrate acima
    # migrate = Migrate(app, db)  <- Este é o problema

    login_manager.login_view = "routes.login"
    login_manager.session_protection = "strong"

    # Definição do filtro para formatação de datas
    @app.template_filter('string_to_date')
    def string_to_date(value):
        try:
            return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
        except (ValueError, TypeError):
            return value  # Retorna a string original se não puder converter

    # Importar e registrar as rotas **após** a criação do app
    from routes import register_routes
    register_routes(app)

    # Criar o banco dentro do contexto da aplicação
    with app.app_context():
        db.create_all()

    return app

# Criar a aplicação
app = create_app()

# app.py  (logo depois de create_app)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import mercadopago, os

def reconciliar_pendentes():
    sdk   = mercadopago.SDK(os.getenv("MERCADOPAGO_ACCESS_TOKEN"))
    ontem = datetime.utcnow() - timedelta(hours=24)

    pendentes = Inscricao.query.filter(
        Inscricao.status_pagamento == "pending",
        Inscricao.created_at < ontem        # adicione created_at se ainda não existir
    ).all()

    for ins in pendentes:
        resp = sdk.payment().get(ins.payment_id)   # armazene payment_id na criação
        if resp["response"]["status"] == "approved":
            ins.status_pagamento = "approved"
            db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(reconciliar_pendentes, "cron", hour=3, minute=0)  # 03:00 UTC
scheduler.start()


@socketio.on('join', namespace='/checkins')
def on_join(data):
    sala = data.get('sala')
    if sala:
        join_room(sala)




# Função que converte um datetime para o horário de Brasília
def convert_to_brasilia(dt):
    # Se a data não for "aware", considere que está em UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    brasilia_tz = pytz.timezone("America/Sao_Paulo")
    return dt.astimezone(brasilia_tz)

# Registro do filtro de template no Flask
@app.template_filter('brasilia')
def brasilia_filter(dt):
    # Se o datetime não tiver informação de fuso (naive), assumimos que está em UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    brasilia_tz = pytz.timezone("America/Sao_Paulo")
    dt_brasilia = dt.astimezone(brasilia_tz)
    return dt_brasilia.strftime("%d/%m/%Y %H:%M:%S")

# Exemplo de rota que utiliza o filtro no template
@app.route("/")
def index():
    now = datetime.utcnow()  # Data em UTC
    # Em um template você utilizaria: {{ now|brasilia }}
    return f"Horário de Brasília: {brasilia_filter(now)}"

# Executar apenas se rodar diretamente
if __name__ == '__main__':
    socketio.run(app, debug=True)
    
from models import Usuario, Cliente, Ministrante  # ou só os que você precisa

@login_manager.user_loader
def load_user(user_id):
    # Tenta carregar como Usuario
    usuario = Usuario.query.get(user_id)
    if usuario:
        return usuario
    
    # Tenta carregar como Cliente
    cliente = Cliente.query.get(user_id)
    if cliente:
        return cliente
    
    # Tenta carregar como Ministrante (opcional)
    ministrante = Ministrante.query.get(user_id)
    if ministrante:
        return ministrante
    
    return None
