from flask import Blueprint, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from extensions import db
from models import Oficina, Inscricao, Evento, Checkin, CertificadoTemplate
from models.user import Cliente
from services.pdf_service import gerar_comprovante_pdf, gerar_certificados_pdf
from services.certificado_service import verificar_criterios_certificado

import os

comprovante_routes = Blueprint('comprovante_routes', __name__)


@comprovante_routes.route('/baixar_comprovante/<int:oficina_id>')
@login_required
def baixar_comprovante(oficina_id):
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash('Oficina não encontrada!', 'danger')
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    # Busca a inscrição do usuário logado nessa oficina
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first()
    if not inscricao:
        flash('Você não está inscrito nesta oficina.', 'danger')
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

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
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    # Verifica se o usuário está inscrito na oficina
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first()
    if not inscricao:
        flash("Você não está inscrito nesta oficina!", "danger")
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    # Define o caminho do certificado
    pdf_path = f"static/certificados/certificado_{current_user.id}_{oficina.id}.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Gera o certificado (mesmo layout do admin, mas apenas para o usuário logado)
    gerar_certificados_pdf(oficina, [inscricao], pdf_path)

    # Retorna o arquivo PDF gerado
    return send_file(pdf_path, as_attachment=True)


@comprovante_routes.route('/gerar_certificado_evento/<int:evento_id>', methods=['GET'])
@login_required
def gerar_certificado_evento_participante(evento_id):
    """Gera certificado do evento se critérios forem atendidos."""
    evento = Evento.query.get_or_404(evento_id)

    ok, pend = verificar_criterios_certificado(current_user.id, evento_id)
    if not ok:
        flash('Não é possível gerar o certificado: ' + '; '.join(pend), 'warning')
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    oficinas_participadas = (
        Oficina.query.join(Checkin, Checkin.oficina_id == Oficina.id)
        .filter(Checkin.usuario_id == current_user.id, Oficina.evento_id == evento_id)
        .all()
    )
    total_horas = sum(int(of.carga_horaria) for of in oficinas_participadas)

    template = CertificadoTemplate.query.filter_by(cliente_id=evento.cliente_id, ativo=True).first()
    if not template:
        flash('Nenhum template de certificado ativo encontrado.', 'danger')
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))
    cliente = Cliente.query.get(evento.cliente_id)

    from services.pdf_service import gerar_certificado_personalizado
    pdf_path = gerar_certificado_personalizado(current_user, oficinas_participadas, total_horas, '', template.conteudo, cliente)
    return send_file(pdf_path, as_attachment=True)


