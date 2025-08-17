from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Oficina, Configuracao
from models.user import Ministrante
import logging

logger = logging.getLogger(__name__)

dashboard_ministrante_routes = Blueprint('dashboard_ministrante_routes', __name__)


@dashboard_ministrante_routes.route('/dashboard_ministrante')
@login_required
def dashboard_ministrante():
    # Log para depuração: exibir o tipo do current_user e seus atributos
    logger.debug("current_user: %s, type: %s", current_user, type(current_user))
    # Se estiver usando UserMixin, current_user pode não ter o atributo 'tipo'
    # Então, usamos isinstance para verificar se é Ministrante.
    if not isinstance(current_user, Ministrante):
        logger.warning("current_user não é uma instância de Ministrante")
        flash('Acesso negado!', 'danger')
        return redirect(url_for('evento_routes.home'))

    # Busca o ministrante logado com base no email (ou use current_user diretamente)
    ministrante_logado = Ministrante.query.filter_by(email=current_user.email).first()
    if not ministrante_logado:
        logger.warning("Ministrante não encontrado no banco de dados")
        flash('Ministrante não encontrado!', 'danger')
        return redirect(url_for('evento_routes.home'))

    # Buscar as oficinas deste ministrante
    oficinas_do_ministrante = Oficina.query.filter_by(ministrante_id=ministrante_logado.id).all()
    # Carrega a configuração e define habilitar_feedback
    config = Configuracao.query.first()
    habilitar_feedback = config.habilitar_feedback if config else False
    logger.debug("Foram encontradas %s oficinas para o ministrante %s", len(oficinas_do_ministrante), ministrante_logado.email)

    return render_template(
        'dashboard_ministrante.html',
        ministrante=ministrante_logado,
        oficinas=oficinas_do_ministrante,
        habilitar_feedback=habilitar_feedback
    )
