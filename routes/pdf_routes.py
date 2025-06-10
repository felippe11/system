from flask_login import login_required
from services.pdf_service import gerar_etiquetas
from . import routes


@routes.route('/gerar_etiquetas/<int:cliente_id>')
@login_required
def gerar_etiquetas_route(cliente_id):
    """Endpoint para gerar etiquetas em PDF para um cliente."""
    return gerar_etiquetas(cliente_id)
