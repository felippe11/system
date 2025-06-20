from flask import Blueprint, send_file, flash, redirect, url_for, request
from flask_login import login_required, current_user
from models import Oficina, Feedback, Evento, Inscricao, Usuario, CampoPersonalizadoCadastro, RespostaCampo
from services.pdf_service import (
    gerar_pdf_inscritos_pdf,
    gerar_lista_frequencia_pdf,
    gerar_certificados_pdf,
    gerar_pdf_feedback
)
from io import BytesIO
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

relatorio_pdf_routes = Blueprint("relatorio_pdf_routes", __name__)

@relatorio_pdf_routes.route('/gerar_pdf_inscritos/<int:oficina_id>')
@login_required
def gerar_inscritos_pdf_route(oficina_id):
    return gerar_pdf_inscritos_pdf(oficina_id)

# faça o mesmo para outras rotas PDF...

@relatorio_pdf_routes.route('/exportar_participantes_evento')
@login_required
def exportar_participantes_evento():
    """Exporta participantes de um evento em XLSX ou PDF."""
    evento_id = request.args.get('evento_id', type=int)
    formato = request.args.get('formato', 'xlsx')
    if not evento_id:
        flash('Evento não encontrado.', 'warning')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))

    evento = Evento.query.get_or_404(evento_id)
    if current_user.tipo == 'cliente' and evento.cliente_id != current_user.id:
        flash('Acesso negado ao evento.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))

    inscricoes = (
        Inscricao.query
        .filter_by(evento_id=evento.id)
        .join(Usuario)
        .all()
    )
    campos_custom = CampoPersonalizadoCadastro.query.filter_by(cliente_id=evento.cliente_id).all()

    headers = ['Nome', 'CPF', 'Email', 'Formação'] + [c.nome for c in campos_custom]
    dados = []
    for insc in inscricoes:
        usuario = insc.usuario
        row = [usuario.nome, usuario.cpf, usuario.email, usuario.formacao]
        for campo in campos_custom:
            resp = RespostaCampo.query.filter_by(
                resposta_formulario_id=usuario.id,
                campo_id=campo.id
            ).first()
            row.append(resp.valor if resp else '')
        dados.append(row)

    if formato == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elementos = [Paragraph(f'Participantes - {evento.nome}', styles['Title']), Spacer(1, 12)]
        tabela = Table([headers] + dados, repeatRows=1)
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#023E8A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        elementos.append(tabela)
        doc.build(elementos)
        buffer.seek(0)
        nome = f'participantes_evento_{evento.id}.pdf'
        return send_file(buffer, as_attachment=True, download_name=nome, mimetype='application/pdf')

    # padrão XLSX
    output = BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = 'Participantes'
    ws.append(headers)
    for row in dados:
        ws.append(row)
    wb.save(output)
    output.seek(0)
    nome = f'participantes_evento_{evento.id}.xlsx'
    return send_file(output, as_attachment=True, download_name=nome, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
