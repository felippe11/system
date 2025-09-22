from flask import Blueprint, send_file, flash, redirect, url_for, request
from flask_login import login_required, current_user
from io import BytesIO
from utils import endpoints

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy import func
from decimal import Decimal

from models import (
    db,
    Oficina,
    Feedback,
    Evento,
    Inscricao,
    Usuario,
    CampoPersonalizadoCadastro,
    RespostaCampoFormulario,
    Checkin,   # mantidos para futuras rotas/uso
    Sorteio,   # mantidos para futuras rotas/uso
    EventoInscricaoTipo,
    Configuracao,
)

from services.pdf_service import (
    gerar_pdf_inscritos_pdf,
    gerar_lista_frequencia_pdf,
    gerar_certificados_pdf,
    gerar_pdf_feedback,
)

from services.relatorio_service import (
    criar_documento_word,
    converter_para_pdf,
    gerar_texto_relatorio,  # usar a versão do relatorio_service
)

relatorio_pdf_routes = Blueprint("relatorio_pdf_routes", __name__)

@relatorio_pdf_routes.route('/gerar_pdf_inscritos/<int:oficina_id>')
@login_required
def gerar_inscritos_pdf_route(oficina_id):
    """Gera um PDF dos inscritos da oficina especificada pelo oficina_id."""
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
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

    evento = Evento.query.get_or_404(evento_id)
    if current_user.tipo == 'cliente' and evento.cliente_id != current_user.id:
        flash('Acesso negado ao evento.', 'danger')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

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
            resp = RespostaCampoFormulario.query.filter_by(
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


@relatorio_pdf_routes.route('/exportar_financeiro')
@login_required
def exportar_financeiro():
    """Exporta o resumo financeiro do cliente em PDF ou XLSX."""
    if current_user.tipo != 'cliente':
        flash('Acesso negado.', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))

    formato = request.args.get('formato', 'xlsx')

    dados = (
        db.session.query(
            EventoInscricaoTipo.nome.label('nome'),
            func.count(Inscricao.id).label('quantidade'),
            EventoInscricaoTipo.preco.label('preco')
        )
        .join(Evento, Evento.id == EventoInscricaoTipo.evento_id)
        .join(Inscricao, Inscricao.tipo_inscricao_id == EventoInscricaoTipo.id)
        .filter(
            Evento.cliente_id == current_user.id,
            Inscricao.status_pagamento == 'approved'
        )
        .group_by(EventoInscricaoTipo.id)
        .order_by(func.count(Inscricao.id).desc())
        .all()
    )

    total = sum(float(r.preco) * r.quantidade for r in dados)

    if formato == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elementos = [Paragraph('Relatório Financeiro', styles['Title']), Spacer(1, 12)]
        tabela = Table([
            ['Tipo', 'Quantidade', 'Valor Unitário']
        ] + [[r.nome, str(r.quantidade), f'R$ {r.preco:.2f}'] for r in dados] + [['Total', '', f'R$ {total:.2f}']],
            repeatRows=1
        )
        tabela.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#023E8A')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        elementos.append(tabela)
        doc.build(elementos)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='financeiro.pdf', mimetype='application/pdf')

    output = BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = 'Financeiro'
    ws.append(['Tipo', 'Quantidade', 'Valor Unitário'])
    for r in dados:
        ws.append([r.nome, r.quantidade, float(r.preco)])
    ws.append(['Total', '', total])
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='financeiro.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@relatorio_pdf_routes.route('/gerar_relatorio_evento/<int:evento_id>', methods=['POST'])
@login_required
def gerar_relatorio_evento(evento_id):
    """Gera relatório detalhado do evento com prévia, Word e PDF."""
    evento = Evento.query.get_or_404(evento_id)
    if current_user.tipo == 'cliente' and evento.cliente_id != current_user.id:
        flash('Acesso negado ao evento.', 'danger')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

    payload = request.get_json() or {}
    dados_selecionados = payload.get('dados', [])
    cabecalho = payload.get('cabecalho', '')
    rodape = payload.get('rodape', '')
    dados_extra = payload.get('dados_extra', {})

    # utiliza a função unificada do relatorio_service
    texto = gerar_texto_relatorio(evento, dados_selecionados)

    docx_buffer = criar_documento_word(texto, cabecalho, rodape, dados_extra)
    pdf_buffer = converter_para_pdf(docx_buffer)

    if request.args.get('preview') == '1':
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, mimetype='application/pdf')

    formato = request.args.get('formato', 'pdf')
    if formato == 'docx':
        docx_buffer.seek(0)
        nome = f'relatorio_evento_{evento.id}.docx'
        return send_file(
            docx_buffer,
            as_attachment=True,
            download_name=nome,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    pdf_buffer.seek(0)
    nome = f'relatorio_evento_{evento.id}.pdf'
    return send_file(pdf_buffer, as_attachment=True, download_name=nome, mimetype='application/pdf')
