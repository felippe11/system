from flask import Blueprint, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from extensions import db
from models import Oficina, Inscricao
from services.pdf_service import gerar_comprovante_pdf, gerar_certificados_pdf

import os

comprovante_routes = Blueprint('comprovante_routes', __name__)


@comprovante_routes.route('/baixar_comprovante/<int:oficina_id>')
@login_required
def baixar_comprovante(oficina_id):
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash('Oficina não encontrada!', 'danger')
        return redirect(url_for('routes.dashboard_participante'))

    # Busca a inscrição do usuário logado nessa oficina
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first()
    if not inscricao:
        flash('Você não está inscrito nesta oficina.', 'danger')
        return redirect(url_for('routes.dashboard_participante'))

    # Agora chamamos a função com o parâmetro adicional "inscricao"
    pdf_path = gerar_comprovante_pdf(current_user, oficina, inscricao)
    return send_file(pdf_path, as_attachment=True)


@comprovante_routes.route('/gerar_certificado/<int:oficina_id>', methods=['GET'])
@login_required
def gerar_certificado_individual(oficina_id):
    """
    Gera um certificado individual para o usuário logado em uma oficina específica.
    """
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash("Oficina não encontrada!", "danger")
        return redirect(url_for('routes.dashboard_participante'))

    # Verifica se o usuário está inscrito na oficina
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first()
    if not inscricao:
        flash("Você não está inscrito nesta oficina!", "danger")
        return redirect(url_for('routes.dashboard_participante'))

    # Define o caminho do certificado
    pdf_path = f"static/certificados/certificado_{current_user.id}_{oficina.id}.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Gera o certificado (mesmo layout do admin, mas apenas para o usuário logado)
    gerar_certificados_pdf(oficina, [inscricao], pdf_path)

    # Retorna o arquivo PDF gerado
    return send_file(pdf_path, as_attachment=True)


