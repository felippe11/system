from flask import Blueprint, send_file, flash, redirect, url_for, request
from flask_login import login_required, current_user
from models import Oficina, Feedback
from services.pdf_service import (
    gerar_pdf_inscritos_pdf,
    gerar_lista_frequencia_pdf,
    gerar_certificados_pdf,
    gerar_pdf_feedback
)

relatorio_pdf_routes = Blueprint("relatorio_pdf_routes", __name__)

@relatorio_pdf_routes.route('/gerar_pdf_inscritos/<int:oficina_id>')
@login_required
def gerar_inscritos_pdf_route(oficina_id):
    return gerar_pdf_inscritos_pdf(oficina_id)

# faça o mesmo para outras rotas PDF...
