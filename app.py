# -*- coding: utf-8 -*-
from flask import (
    Flask,
    url_for as flask_url_for,
    send_from_directory,
    request,
    jsonify,
    redirect,
)
from flask_cors import CORS
from flask_socketio import join_room
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from config import Config, normalize_pg
from extensions import db, login_manager, migrate, mail, socketio, csrf
from models import Inscricao
import pytz
import logging
import os

# Configuração centralizada de logging
logging.basicConfig(
    level=logging.DEBUG if Config.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


from services.mp_service import get_sdk
from utils.dia_semana import dia_semana


def create_app():
    """Create and configure the Flask application.

    Initializes extensions, registers routes and filters, and schedules
    background tasks required by the project.

    Returns:
        Flask: Configured application instance ready to serve requests.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    # Normaliza o URI para garantir que seja uma string
    app.config["SQLALCHEMY_DATABASE_URI"] = normalize_pg(
        app.config["SQLALCHEMY_DATABASE_URI"]
    )
    # Recalcula as opções de conexão caso o URI tenha sido alterado nos testes
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.build_engine_options(
        app.config["SQLALCHEMY_DATABASE_URI"]
    )
    app.jinja_env.add_extension("jinja2.ext.do")
    app.config["UPLOAD_FOLDER"] = "uploads"

    # Inicialização de extensões
    socketio.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    csrf.init_app(app)
    CORS(app)

    # CSRF error handler for API endpoints
    from flask_wtf.csrf import CSRFError
    from flask import jsonify, request
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Skip CSRF validation for distribution endpoints
        if request.path in ['/api/distribution/manual', '/api/distribution/automatic']:
            return None  # Let the request proceed without CSRF validation
        # Check if this is an API request (starts with /api/ or has JSON content type)
        if request.path.startswith('/api/') or request.content_type == 'application/json' or 'application/json' in request.headers.get('Accept', ''):
            return jsonify({
                'error': 'CSRF token missing or invalid',
                'message': 'Token CSRF ausente ou inválido'
            }), 400
        # For non-API requests, return the default HTML error
        return e.description, 400

    login_manager.login_view = "auth_routes.login"
    login_manager.session_protection = "strong"

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        """Return JSON for unauthorized AJAX requests."""
        if (
            request.accept_mimetypes["application/json"]
            >= request.accept_mimetypes["text/html"]
        ):
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        return redirect(flask_url_for(login_manager.login_view))

    # Cache busting para arquivos estáticos
    def versioned_url_for(endpoint, **values):
        if endpoint == "static":
            filename = values.get("filename")
            if filename:
                file_path = os.path.join(app.static_folder, filename)
                if os.path.exists(file_path):
                    values["v"] = int(os.stat(file_path).st_mtime)
        return flask_url_for(endpoint, **values)

    @app.context_processor
    def override_url_for():
        return dict(url_for=versioned_url_for)

    # Filtros Jinja2
    @app.template_filter("string_to_date")
    def string_to_date(value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return value

    @app.template_filter("brasilia")
    def brasilia_filter(dt):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.utc)
        dt_brasilia = dt.astimezone(pytz.timezone("America/Sao_Paulo"))
        return dt_brasilia.strftime("%d/%m/%Y %H:%M:%S")

    @app.template_filter("utc_iso")
    def utc_iso_filter(dt):
        """Convert datetime to UTC ISO format for JavaScript processing"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.utc)
        else:
            dt = dt.astimezone(pytz.utc)
        return dt.isoformat()


    @app.template_filter("dia_semana")
    def dia_semana_filter(value):
        return dia_semana(value)


    # Registro de rotas
    from routes import register_routes
    register_routes(app)
    

    # Registro do contexto de autorização para templates
    from utils.template_context import register_template_context
    register_template_context(app)
    

    # Registro de rotas de diagnóstico (opcional em desenvolvimento)
    enable_debug_routes = Config.DEBUG or os.getenv("ENABLE_DIAGNOSTIC_ROUTES") == "1"

    if enable_debug_routes:
        try:
            from routes.debug_recaptcha_routes import debug_recaptcha_routes
            app.register_blueprint(debug_recaptcha_routes)
            app.logger.info(
                "Rotas de diagnóstico de reCAPTCHA habilitadas"
            )
        except ImportError as e:
            app.logger.warning(
                "Não foi possível carregar rotas de diagnóstico: %s", e
            )
    else:
        app.logger.info(
            "Rotas de diagnóstico de reCAPTCHA desabilitadas"
        )

    # Ensure default submission form exists
    with app.app_context():
        from models.formulario import ensure_formulario_trabalhos

        ensure_formulario_trabalhos()

    @app.cli.command("check-formulario-trabalhos")
    def check_formulario_trabalhos_command():
        """Verify the presence of the default submission form."""
        from models.formulario import formulario_trabalhos_exists

        if formulario_trabalhos_exists():
            app.logger.info("Formulário de Trabalhos presente.")
        else:
            app.logger.error(
                "Formulário de Trabalhos ausente. Execute "
                "scripts/executar_formulario_trabalhos.py"
            )

    # Agendamento do reconciliador e rotas utilitárias são registrados aqui
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        reconciliar_pendentes, "cron", hour=3, minute=0, args=[app]
    )
    scheduler.start()

    @socketio.on("join", namespace="/checkins")
    def on_join(data):
        sala = data.get("sala")
        if sala:
            join_room(sala)

    @app.route("/time")
    def current_time():
        now = datetime.utcnow()
        return "Horario de Brasilia: " + str(brasilia_filter(now))
    
    # Rota de debug temporária para testar modal
    @app.route("/debug-modal")
    def debug_modal():
        from flask import render_template
        return render_template('debug_modal.html')
    
    # Rota de debug temporária para testar formulário
    @app.route("/debug-form")
    def debug_form():
        from flask import render_template
        return render_template('test_form_debug.html')
    
    # Rota de debug temporária para testar botão gerar-codigos
    @app.route("/debug-gerar-codigos")
    def debug_gerar_codigos():
        from flask import render_template
        return render_template('test_gerar_codigos.html')
    
    # Rota de debug temporária para testar função avancarParaEtapa4
    @app.route("/debug-avancar")
    def debug_avancar():
        from flask import render_template
        return render_template('debug_test.html')
    


    return app


# Função para reconciliar pagamentos pendentes
def reconciliar_pendentes(app):
    """Reconcile pending payments with Mercado Pago.

    Retrieves ``Inscricao`` records with status ``pending`` that are older than
    24 hours and checks each payment via the Mercado Pago SDK. Approved
    payments have their status updated in the database. If the SDK cannot be
    initialized, the function exits without making changes.

    Args:
        app (Flask): The Flask application instance.

    Returns:
        None: This function does not return a value.

    Exceptions:
        Any database commit error is caught, the session is rolled back, and
        the error is logged.
    """
    with app.app_context():
        sdk = get_sdk()
        if not sdk:
            return
        ontem = datetime.utcnow() - timedelta(hours=24)
        pendentes = Inscricao.query.filter(
            Inscricao.status_pagamento == "pending", Inscricao.created_at < ontem
        ).all()

        reconciled = []
        for ins in pendentes:
            resp = sdk.payment().get(ins.payment_id)
            if resp["response"]["status"] == "approved":
                ins.status_pagamento = "approved"
                reconciled.append(ins)

        if reconciled:
            try:
                db.session.commit()
                logging.info("Reconciled %d pending payments", len(reconciled))
            except Exception:
                db.session.rollback()
                logging.exception("Failed to commit reconciled payments")


# Execução da aplicação
if __name__ == "__main__":
    # Instância para servidores WSGI como o gunicorn
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    socketio.run(app, debug=True, port=port)
