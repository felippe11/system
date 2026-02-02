from flask import Blueprint, send_file, flash, redirect, url_for, request, current_app, render_template
from flask_login import login_required, current_user
from io import BytesIO
from utils import endpoints

from openpyxl import Workbook

try:  # Algumas instalações (como sandbox de testes) não incluem o ReportLab
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover - caminho de fallback
    REPORTLAB_AVAILABLE = False
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
from datetime import datetime

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
        if not REPORTLAB_AVAILABLE:
            flash('Geração em PDF indisponível no momento; exportando em XLSX.', 'warning')
            current_app.logger.warning('ReportLab não instalado; fallback para XLSX em exportar_participantes_evento.')
            formato = 'xlsx'
        else:
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
        if not REPORTLAB_AVAILABLE:
            flash('Geração em PDF indisponível no momento; exportando em XLSX.', 'warning')
            current_app.logger.warning('ReportLab não instalado; fallback para XLSX em exportar_financeiro.')
            formato = 'xlsx'
        else:
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


@relatorio_pdf_routes.route('/exportar_relatorio_evento/<int:evento_id>', methods=['POST'])
@login_required
def exportar_relatorio_evento(evento_id):
    """Gera relatório detalhado do evento com prévia, Word e PDF (API)."""
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


@relatorio_pdf_routes.route('/gerar_relatorio_evento/<int:evento_id>')
@login_required
def gerar_relatorio_evento(evento_id):
    """Dashboard interativo de relatório do evento."""
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificação de permissão
    if current_user.tipo == 'cliente' and evento.cliente_id != current_user.id:
        flash('Acesso negado ao evento.', 'danger')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
        
    # Coleta de dados para o dashboard
    total_inscritos = Inscricao.query.filter_by(evento_id=evento.id).count()
    
    # Check-ins (Assumindo que Checkin tem relacionamento com Oficina ou Evento, 
    # aqui buscamos via oficinas do evento pois Checkin geralmente é por oficina/atividade)
    oficinas_ids = [o.id for o in evento.oficinas]
    total_presentes = 0
    if oficinas_ids:
        total_presentes = Checkin.query.filter(Checkin.oficina_id.in_(oficinas_ids)).count()
    
    # Receita (Inscrições aprovadas)
    receita_total = db.session.query(func.sum(InscricaoTipo.preco))\
        .join(Inscricao, Inscricao.tipo_inscricao_id == InscricaoTipo.id)\
        .filter(Inscricao.evento_id == evento.id, Inscricao.status_pagamento == 'approved')\
        .scalar() or 0.0
        
    # Satisfação (Feedbacks)
    feedbacks = db.session.query(Feedback)\
        .join(Oficina, Feedback.oficina_id == Oficina.id)\
        .filter(Oficina.evento_id == evento.id).all()
        
    media_avaliacao = 0
    nps = 0
    if feedbacks:
        notas = [f.rating for f in feedbacks if f.rating]
        if notas:
            media_avaliacao = sum(notas) / len(notas)
            
            # Cálculo NPS simplificado
            promotores = len([n for n in notas if n >= 4]) # Adapte conforme escala (1-5 ou 0-10)
            detratores = len([n for n in notas if n <= 2])
            nps = ((promotores - detratores) / len(notas)) * 100

    # Ultimas inscrições para tabela
    ultimas_inscricoes = Inscricao.query.filter_by(evento_id=evento.id)\
        .order_by(Inscricao.created_at.desc())\
        .limit(10).all()

    return render_template(
        'relatorio/evento_dashboard.html',
        evento=evento,
        kpis={
            'inscritos': total_inscritos,
            'presentes': total_presentes,
            'receita': receita_total,
            'satisfacao': media_avaliacao,
            'nps': int(nps)
        },
        ultimas_inscricoes=ultimas_inscricoes,
        now=datetime.now()
    )
