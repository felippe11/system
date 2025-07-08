from flask_login import login_required
from flask import request, send_file, redirect, url_for
import os
from services.pdf_service import (
    gerar_etiquetas,
    gerar_pdf_checkins_qr as gerar_pdf_checkins_qr_service,
    gerar_pdf_feedback_route as gerar_pdf_feedback_service,
    gerar_pdf_inscritos_pdf,
    gerar_lista_frequencia,
    gerar_certificados,
    gerar_certificados_pdf,
    gerar_evento_qrcode_pdf,
    gerar_qrcode_token,
    gerar_programacao_evento_pdf,
    gerar_placas_oficinas_pdf,
    exportar_checkins_pdf_opcoes,
)
from . import routes


@routes.route('/gerar_etiquetas/<int:cliente_id>')
@login_required
def gerar_etiquetas_route(cliente_id):
    """Endpoint para gerar etiquetas em PDF para um cliente."""
    return gerar_etiquetas(cliente_id)


@routes.route('/gerar_pdf_checkins/<int:oficina_id>')
@login_required
def gerar_pdf_checkins(oficina_id):
    """Gera relatório de check-ins em PDF."""
    # A função existente não usa o ID da oficina, mas mantemos o parâmetro
    return gerar_pdf_checkins_qr_service()


@routes.route('/gerar_pdf_checkins_qr')
@login_required
def gerar_pdf_checkins_qr():
    """Relatório de check-ins via QR Code."""
    return gerar_pdf_checkins_qr_service()


@routes.route('/gerar_pdf_inscritos/<int:oficina_id>')
@login_required
def gerar_pdf_inscritos_pdf_route(oficina_id):
    return gerar_pdf_inscritos_pdf(oficina_id)


@routes.route('/gerar_lista_frequencia/<int:oficina_id>')
@login_required
def gerar_lista_frequencia_route(oficina_id):
    return gerar_lista_frequencia(oficina_id)


@routes.route('/gerar_certificados/<int:oficina_id>')
@login_required
def gerar_certificados_route(oficina_id):
    return gerar_certificados(oficina_id)


@routes.route('/gerar_pdf_feedback/<int:oficina_id>')
@login_required
def gerar_pdf_feedback_route(oficina_id):
    """Gera um PDF com os feedbacks da oficina."""
    return gerar_pdf_feedback_service(oficina_id)


@routes.route('/gerar_certificado_individual_admin', methods=['GET', 'POST'])
@login_required
def gerar_certificado_individual_admin():
    if request.method == 'POST':
        oficina_id = request.form.get('oficina_id', type=int)
        usuario_id = request.form.get('usuario_id', type=int)
    else:
        oficina_id = request.args.get('oficina_id', type=int)
        usuario_id = request.args.get('usuario_id', type=int)
    from models import Oficina, Inscricao

    oficina = Oficina.query.get_or_404(oficina_id)
    inscricao = Inscricao.query.filter_by(usuario_id=usuario_id, oficina_id=oficina.id).first_or_404()

    pdf_path = f"static/certificados/certificado_{usuario_id}_{oficina.id}.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    gerar_certificados_pdf(oficina, [inscricao], pdf_path)
    return send_file(pdf_path, as_attachment=True)


@routes.route('/gerar_evento_qrcode_pdf/<int:evento_id>')
@login_required
def gerar_evento_qrcode_pdf_route(evento_id):
    return gerar_evento_qrcode_pdf(evento_id)


@routes.route('/gerar_qrcode_token/<token>')
def gerar_qrcode_token_route(token):
    return gerar_qrcode_token(token)


@routes.route('/gerar_folder_evento/<int:evento_id>')
def gerar_folder_evento(evento_id):
    return gerar_programacao_evento_pdf(evento_id)


@routes.route('/gerar_placas/<int:evento_id>')
@login_required
def gerar_placas_oficinas(evento_id):
    """Gera PDF com placas simples das oficinas do evento."""
    return gerar_placas_oficinas_pdf(evento_id)


@routes.route('/exportar_checkins_filtrados')
@login_required
def exportar_checkins_filtrados():
    """Gera PDF de check-ins aplicando filtros de evento e tipo."""
    return exportar_checkins_pdf_opcoes()
