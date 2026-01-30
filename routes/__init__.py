import logging

from flask import Blueprint

# Cria o Blueprint principal
routes = Blueprint("routes", __name__)

# Usuários com pagamento pendente continuam com acesso liberado, portanto
# nenhum middleware de bloqueio é aplicado ao blueprint.

def register_routes(app):
    """Register all route blueprints with the given Flask app.

    Args:
        app (Flask): Application instance to attach blueprints to.

    The function mutates ``app`` by registering multiple blueprints.
    """

    # Importações e registros dos Blueprints de módulos organizados
    from .auth_routes import auth_routes
    from .dashboard_routes import dashboard_routes
    # Importa rotas adicionais do cliente que utilizam o mesmo blueprint
    from . import dashboard_cliente  # noqa: F401
    try:
        from . import pdf_routes  # noqa: F401
    except Exception as e:  # pragma: no cover - optional deps
        logging.getLogger(__name__).info("pdf_routes disabled: %s", e)
    from .dashboard_participante import dashboard_participante_routes
    from .dashboard_professor import dashboard_professor_routes
    from .dashboard_ministrante import dashboard_ministrante_routes

    from .evento_routes import evento_routes
    from .oficina_routes import oficina_routes
    from .inscricao_routes import inscricao_routes
    from .participante_routes import participante_routes
    from .ministrante_routes import ministrante_routes
    from .proposta_routes import proposta_routes
    from .formularios_routes import formularios_routes
    from .trabalho_routes import trabalho_routes
    from .patrocinador_routes import patrocinador_routes
    from .campo_routes import campo_routes
    from .checkin_routes import checkin_routes
    from .atividade_multipla_routes import atividade_multipla_routes
    from .feedback_routes import feedback_routes
    from .reminder_routes import reminder_routes
    from .config_cliente_routes import config_cliente_routes
    from .relatorio_routes import relatorio_routes
    from .relatorio_bi_routes import relatorio_bi_routes
    from .gerar_link_routes import gerar_link_routes
    from .comprovante_routes import comprovante_routes
    from .certificado_routes import certificado_routes
    from .certificado_revisor_routes import certificado_revisor_routes
    from .placeholder_routes import placeholder_routes
    from . import professor_routes  # noqa: F401
    from .agendamento_routes import agendamento_routes
    from .cliente_routes import cliente_routes
    from .importar_usuarios_routes import importar_usuarios_routes
    from .sorteio_routes import sorteio_routes
    from .api_cidades import api_cidades
    from .mercadopago_routes import mercadopago_routes
    from .binary_routes import binary_routes
    from .reviewer_routes import reviewer_routes
    from .revisor_routes import revisor_routes
    from .peer_review_routes import peer_review_routes
    from .submission_routes import submission_routes
    from .util_routes import util_routes
    from .relatorio_pdf_routes import relatorio_pdf_routes
    from .static_page_routes import static_page_routes
    from .monitor_routes import monitor_routes
    from .material_routes import material_routes
    from .compra_routes import compra_routes
    from .aprovacao_routes import aprovacao_routes
    from .orcamento_routes import orcamento_bp
    from .ai_routes import ai_bp
    from .validacao_routes import validacao_bp
    from .declaracao_routes import declaracao_bp
    try:
        from .editor_routes import editor_bp
    except ImportError as exc:  # pragma: no cover - optional module
        editor_bp = None
        logging.getLogger(__name__).info("editor_routes disabled: %s", exc)

    from .importar_trabalhos_routes import importar_trabalhos_routes
    
    # Novas rotas do sistema de formador
    from .formador_routes import formador_routes
    from .monitor_formador_routes import monitor_formador_routes
    from .cliente_formador_routes import cliente_formador_routes
    from .formador_relatorio_routes import formador_relatorio_routes

    from .secure_file_routes import secure_file_routes
    from .submission_distribution_routes import submission_distribution_routes
    from .favicon_routes import favicon_routes
    from .voting_routes import voting_routes

    # Importa servicos que registram rotas diretamente no blueprint
    from services import lote_service  # noqa: F401

    # Registra o blueprint principal somente após importar rotas que o utilizam
    app.register_blueprint(routes)

    # Registro dos Blueprints
    app.register_blueprint(auth_routes)
    app.register_blueprint(dashboard_routes)
    app.register_blueprint(dashboard_participante_routes)
    app.register_blueprint(dashboard_professor_routes)
    app.register_blueprint(dashboard_ministrante_routes)

    app.register_blueprint(evento_routes)
    app.register_blueprint(oficina_routes)
    app.register_blueprint(inscricao_routes)
    app.register_blueprint(participante_routes)
    app.register_blueprint(ministrante_routes)
    app.register_blueprint(proposta_routes)
    app.register_blueprint(formularios_routes)
    app.register_blueprint(trabalho_routes)
    app.register_blueprint(patrocinador_routes)
    app.register_blueprint(campo_routes)
    app.register_blueprint(checkin_routes)
    app.register_blueprint(atividade_multipla_routes)
    app.register_blueprint(feedback_routes)
    app.register_blueprint(reminder_routes)
    app.register_blueprint(config_cliente_routes)
    app.register_blueprint(relatorio_routes)
    app.register_blueprint(relatorio_bi_routes)
    app.register_blueprint(gerar_link_routes)
    app.register_blueprint(comprovante_routes)
    app.register_blueprint(agendamento_routes)
    app.register_blueprint(cliente_routes)
    app.register_blueprint(importar_usuarios_routes)
    app.register_blueprint(sorteio_routes)
    app.register_blueprint(api_cidades)
    app.register_blueprint(mercadopago_routes)
    app.register_blueprint(binary_routes)
    app.register_blueprint(reviewer_routes)
    app.register_blueprint(revisor_routes)
    app.register_blueprint(submission_routes)
    app.register_blueprint(util_routes)
    app.register_blueprint(relatorio_pdf_routes)
    app.register_blueprint(certificado_routes)
    app.register_blueprint(certificado_revisor_routes)
    app.register_blueprint(placeholder_routes)
    app.register_blueprint(static_page_routes)
    app.register_blueprint(peer_review_routes)
    app.register_blueprint(monitor_routes)
    app.register_blueprint(material_routes)
    app.register_blueprint(compra_routes)
    app.register_blueprint(aprovacao_routes)
    app.register_blueprint(orcamento_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(validacao_bp)
    app.register_blueprint(declaracao_bp)
    if editor_bp:
        app.register_blueprint(editor_bp)

    app.register_blueprint(importar_trabalhos_routes)

    app.register_blueprint(secure_file_routes)
    app.register_blueprint(submission_distribution_routes)
    app.register_blueprint(favicon_routes)
    app.register_blueprint(voting_routes)
    
    # Registro das novas rotas do sistema de formador
    app.register_blueprint(formador_routes)
    app.register_blueprint(monitor_formador_routes)
    app.register_blueprint(cliente_formador_routes)
    app.register_blueprint(formador_relatorio_routes)


