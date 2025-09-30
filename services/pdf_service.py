from flask_login import login_required
from utils import external_url, determinar_turno
from utils.dia_semana import dia_semana
from fpdf import FPDF
from datetime import datetime
import logging
import psutil
import os
import time
import uuid
import tempfile
import re
import textwrap
from html import unescape
from flask import current_app
from utils import endpoints

logger = logging.getLogger(__name__)


def _profile(func):
    """Log memory usage and execution time around heavy tasks."""
    def wrapper(*args, **kwargs):
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            duration = time.perf_counter() - start
            mem_after = process.memory_info().rss
            logger.info(
                "%s took %.2fs | mem %.2f -> %.2f MB",
                func.__name__,
                duration,
                mem_before / (1024 * 1024),
                mem_after / (1024 * 1024),
            )

    return wrapper


STYLE_DELIMITER_RE = re.compile(r';')
TAG_RE = re.compile(r'<[^>]+>')
NUMBER_RE = re.compile(r'([-+]?[0-9]*\.?[0-9]+)')


def _parse_style_dict(style_str):
    if not style_str:
        return {}
    styles = {}
    for raw in STYLE_DELIMITER_RE.split(style_str):
        if ':' not in raw:
            continue
        key, value = raw.split(':', 1)
        styles[key.strip().lower()] = value.strip()
    return styles


def _parse_px(value, default):
    if not value:
        return float(default)
    match = NUMBER_RE.search(str(value))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return float(default)
    return float(default)


def _parse_color(value, default=None):
    from reportlab.lib import colors

    if default is None:
        default = colors.black
    if not value:
        return default

    value = value.strip()
    try:
        if value.startswith('#'):
            if len(value) == 4:
                value = '#' + ''.join(ch * 2 for ch in value[1:])
            return colors.HexColor(value)
        if value.startswith('rgb'):
            nums = [float(part) for part in NUMBER_RE.findall(value)[:3]]
            if len(nums) == 3:
                return colors.Color(*(n / 255.0 for n in nums))
        if value:
            return colors.HexColor('#' + value.replace('#', ''))
    except Exception:
        pass
    return default


def _extract_text(html_value):
    if not html_value:
        return ''
    text = html_value.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    text = TAG_RE.sub('', text)
    return unescape(text).strip()


def _extract_image_src(html_value):
    if not html_value:
        return None
    match = re.search(r'src\s*=\s*"([^"]+)"', html_value)
    if match:
        return match.group(1)
    match = re.search(r"src\s*=\s*'([^']+)'", html_value)
    if match:
        return match.group(1)
    return None


def _resolve_image_path(src):
    if not src:
        return None
    if src.startswith('data:'):
        return None
    if src.startswith('http'):
        return None

    cleaned = src.lstrip('/')
    candidates = []

    if os.path.isabs(src) and os.path.exists(src):
        return src

    try:
        app = current_app._get_current_object()
    except RuntimeError:
        app = None

    if app:
        candidates.append(os.path.join(app.root_path, cleaned))
        if app.static_folder:
            candidates.append(os.path.join(app.static_folder, cleaned))

    candidates.append(src)

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


@_profile
def gerar_certificado_revisor_pdf(certificado):
    """Gera PDF do certificado de revisor."""
    from models import CertificadoRevisor
    
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Usar fontes padrão do FPDF (Arial)
    # Não precisa carregar fontes externas
    
    # Definir margens
    margin_left = 20
    margin_top = 20
    page_width = 297  # A4 landscape width
    page_height = 210  # A4 landscape height
    
    # Adicionar fundo se configurado
    if certificado.fundo_personalizado and os.path.exists(os.path.join('static', certificado.fundo_personalizado)):
        pdf.image(os.path.join('static', certificado.fundo_personalizado), 0, 0, page_width, page_height)
    
    # Título do certificado
    pdf.set_font('Arial', 'B', 24)
    pdf.set_text_color(0, 0, 0)
    titulo_width = pdf.get_string_width(certificado.titulo)
    pdf.set_xy((page_width - titulo_width) / 2, margin_top + 20)
    pdf.cell(titulo_width, 10, certificado.titulo, 0, 1, 'C')
    
    # Espaçamento
    pdf.set_xy(0, margin_top + 50)
    
    # Texto do certificado com substituição de variáveis
    texto = certificado.texto_personalizado or certificado.titulo
    
    # Substituir variáveis
    texto = texto.replace('{nome_revisor}', certificado.revisor.nome)
    texto = texto.replace('{evento_nome}', certificado.evento.nome if certificado.evento else '')
    texto = texto.replace('{cliente_nome}', certificado.cliente.nome)
    texto = texto.replace('{trabalhos_revisados}', str(certificado.trabalhos_revisados))
    texto = texto.replace('{data_liberacao}', certificado.data_liberacao.strftime('%d/%m/%Y') if certificado.data_liberacao else '')
    
    # Dividir texto em linhas
    pdf.set_font('Arial', '', 14)
    pdf.set_text_color(0, 0, 0)
    
    # Calcular largura disponível para texto
    text_width = page_width - (margin_left * 2)
    
    # Quebrar texto em linhas
    words = texto.split(' ')
    lines = []
    current_line = ''
    
    for word in words:
        test_line = current_line + (' ' if current_line else '') + word
        if pdf.get_string_width(test_line) <= text_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    # Escrever linhas centralizadas
    line_height = 8
    start_y = margin_top + 80
    
    for i, line in enumerate(lines):
        y_pos = start_y + (i * line_height)
        pdf.set_xy(margin_left, y_pos)
        pdf.cell(text_width, line_height, line, 0, 1, 'C')
    
    # Informações adicionais
    info_y = start_y + (len(lines) * line_height) + 20
    
    # Data de emissão
    pdf.set_font('Arial', '', 12)
    pdf.set_xy(margin_left, info_y)
    pdf.cell(text_width, 8, f"Emitido em: {certificado.data_liberacao.strftime('%d/%m/%Y') if certificado.data_liberacao else datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'C')
    
    # Assinatura do cliente (condicional)
    # Verificar se deve incluir assinatura baseado na configuração
    incluir_assinatura = True  # Padrão
    
    # Buscar configuração do certificado
    try:
        from models import CertificadoRevisorConfig
        config = CertificadoRevisorConfig.query.filter_by(
            cliente_id=certificado.cliente_id,
            evento_id=certificado.evento_id
        ).first()
        
        if config:
            incluir_assinatura = config.incluir_assinatura_cliente
    except Exception as e:
        logger.warning(f"Erro ao verificar configuração de assinatura: {e}")
        incluir_assinatura = True  # Manter padrão em caso de erro
    
    if incluir_assinatura:
        assinatura_y = info_y + 30
        pdf.set_font('Arial', '', 12)
        pdf.set_xy(margin_left, assinatura_y)
        pdf.cell(text_width, 8, certificado.cliente.nome, 0, 1, 'C')
        
        # Linha para assinatura
        pdf.set_xy(margin_left + (text_width / 2) - 30, assinatura_y + 15)
        pdf.line(margin_left + (text_width / 2) - 30, assinatura_y + 15, margin_left + (text_width / 2) + 30, assinatura_y + 15)
    
    # Gerar arquivo
    filename = f"certificado_revisor_{certificado.id}_{uuid.uuid4().hex[:8]}.pdf"
    pdf_path = os.path.join('static', 'certificados', 'revisores')
    os.makedirs(pdf_path, exist_ok=True)
    full_path = os.path.join(pdf_path, filename)
    
    pdf.output(full_path)
    
    return full_path


def gerar_revisor_details_pdf(cand, pdf_path=None):
    """Gera um PDF estilo bilhete de cinema com dados do revisor."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    import tempfile
    import os
    from flask import send_file
    from textwrap import wrap
    from datetime import datetime

    if pdf_path is None:
        pdf_filename = f"comprovante_revisor_{cand.codigo}.pdf"
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)

    # Formato bilhete de cinema (mais largo e menos alto)
    c = canvas.Canvas(pdf_path, pagesize=(612, 396), pageCompression=0)  # 8.5x5.5 inches
    width, height = 612, 396
    
    # Cores do tema bilhete de cinema
    cor_principal = colors.HexColor('#1a1a1a')      # Preto
    cor_secundaria = colors.HexColor('#ff6b35')      # Laranja vibrante
    cor_dourado = colors.HexColor('#ffd700')        # Dourado
    cor_texto = colors.HexColor('#2c2c2c')          # Cinza escuro
    cor_fundo = colors.HexColor('#ffffff')           # Branco
    cor_borda = colors.HexColor('#e0e0e0')          # Cinza claro
    
    # Fundo branco
    c.setFillColor(cor_fundo)
    c.rect(0, 0, width, height, fill=1)
    
    # Bordas externas
    c.setStrokeColor(cor_borda)
    c.setLineWidth(2)
    c.rect(10, 10, width-20, height-20, fill=0)
    
    # Cabeçalho principal - estilo cinema
    c.setFillColor(cor_principal)
    c.rect(15, height-80, width-30, 70, fill=1)
    
    # Título principal em dourado
    c.setFillColor(cor_dourado)
    c.setFont("Helvetica-Bold", 28)
    titulo = "COMPROVANTE DE CANDIDATURA"
    titulo_width = c.stringWidth(titulo, "Helvetica-Bold", 28)
    c.drawString((width - titulo_width) / 2, height - 45, titulo)
    
    # Subtítulo em branco
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 16)
    subtitulo = "Revisor de Trabalhos Científicos"
    subtitulo_width = c.stringWidth(subtitulo, "Helvetica", 16)
    c.drawString((width - subtitulo_width) / 2, height - 70, subtitulo)
    
    # Linha decorativa laranja
    c.setFillColor(cor_secundaria)
    c.rect(15, height-85, width-30, 5, fill=1)
    
    # Seção principal - dados do revisor
    y_pos = height - 120
    
    # Card principal com bordas arredondadas simuladas
    c.setFillColor(cor_fundo)
    c.setStrokeColor(cor_secundaria)
    c.setLineWidth(3)
    c.rect(25, y_pos - 30, width-50, 180, fill=1)
    
    # Título da seção
    c.setFillColor(cor_principal)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(40, y_pos, "DADOS DO REVISOR")
    
    # Linha decorativa
    c.setFillColor(cor_secundaria)
    c.rect(40, y_pos - 5, width-80, 2, fill=1)
    
    y_pos -= 35
    
    # Dados principais em duas colunas
    c.setFillColor(cor_texto)
    c.setFont("Helvetica-Bold", 14)
    
    # Coluna esquerda
    c.drawString(40, y_pos, "NOME:")
    c.setFont("Helvetica", 14)
    c.drawString(40, y_pos - 20, cand.nome)
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos - 45, "E-MAIL:")
    c.setFont("Helvetica", 14)
    c.drawString(40, y_pos - 65, cand.email)
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos - 90, "CÓDIGO:")
    c.setFont("Helvetica", 14)
    c.drawString(40, y_pos - 110, cand.codigo)
    
    # Coluna direita
    c.setFont("Helvetica-Bold", 14)
    c.drawString(width/2 + 20, y_pos, "STATUS:")
    c.setFont("Helvetica", 14)
    status_text = cand.status.upper() if cand.status else "PENDENTE"
    c.drawString(width/2 + 20, y_pos - 20, status_text)
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(width/2 + 20, y_pos - 45, "DATA:")
    c.setFont("Helvetica", 14)
    c.drawString(width/2 + 20, y_pos - 65, datetime.now().strftime("%d/%m/%Y"))
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(width/2 + 20, y_pos - 90, "HORA:")
    c.setFont("Helvetica", 14)
    c.drawString(width/2 + 20, y_pos - 110, datetime.now().strftime("%H:%M"))
    
    # Seção de respostas (se houver) - estilo bilhete
    respostas = cand.respostas or {}
    if respostas:
        y_pos -= 140
        
        # Card de respostas
        c.setFillColor(cor_fundo)
        c.setStrokeColor(cor_secundaria)
        c.setLineWidth(2)
        c.rect(25, y_pos - 20, width-50, 100, fill=1)
        
        # Título da seção
        c.setFillColor(cor_principal)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y_pos, "INFORMAÇÕES ADICIONAIS")
        
        # Linha decorativa
        c.setFillColor(cor_secundaria)
        c.rect(40, y_pos - 5, width-80, 2, fill=1)
        
        y_pos -= 25
        
        c.setFillColor(cor_texto)
        c.setFont("Helvetica", 11)
        
        for campo, valor in list(respostas.items())[:4]:  # Limitar a 4 campos
            if isinstance(valor, str) and ("/" in valor or "\\" in valor):
                display_value = os.path.basename(valor) or "arquivo anexado"
            else:
                display_value = str(valor)[:40] + "..." if len(str(valor)) > 40 else str(valor)
            
            c.drawString(40, y_pos, f"• {campo}: {display_value}")
            y_pos -= 18
    
    # Rodapé estilo bilhete de cinema
    c.setFillColor(cor_principal)
    c.rect(15, 15, width-30, 40, fill=1)
    
    # Linha decorativa dourada
    c.setFillColor(cor_dourado)
    c.rect(15, 50, width-30, 3, fill=1)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 10)
    rodape_text = f"Documento gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
    rodape_width = c.stringWidth(rodape_text, "Helvetica", 10)
    c.drawString((width - rodape_width) / 2, 30, rodape_text)
    
    # Código de barras simulado (linhas verticais)
    c.setStrokeColor(cor_principal)
    c.setLineWidth(1)
    for i in range(0, width-40, 3):
        altura = 15 + (i % 10)
        c.line(20 + i, 15, 20 + i, 15 + altura)
    
    c.save()

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=os.path.basename(pdf_path),
    )

@_profile
def gerar_lista_frequencia_pdf(oficina, pdf_path):
    """
    Generates a modern and professional attendance list PDF for a workshop.
    
    Args:
        oficina: The workshop object containing all relevant information
        pdf_path: The file path where the PDF will be saved
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import mm, inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import os
    from datetime import datetime

    # Create custom styles
    styles = getSampleStyleSheet()
    
    # Custom title style
    title_style = ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        textColor=colors.HexColor("#023E8A"),
        spaceAfter=10,
        alignment=TA_CENTER
    )
    
    # Custom heading styles
    heading_style = ParagraphStyle(
        name='CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor("#023E8A"),
        spaceBefore=12,
        spaceAfter=6
    )
    
    # Custom normal text style
    normal_style = ParagraphStyle(
        name='CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceBefore=6,
        spaceAfter=6
    )
    
    # Info style for workshop details
    info_style = ParagraphStyle(
        name='InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        leftIndent=5 * mm,
        textColor=colors.HexColor("#444444")
    )
    
    # Setup document with proper margins
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )
    
    elements = []
    
    # Add header with logo (if available)
    logo_path = os.path.join("static", "logos", "company_logo.png")
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=50 * mm, height=15 * mm, hAlign='CENTER'))
        elements.append(Spacer(1, 5 * mm))
    
    # Add title and current date
    current_date = datetime.now().strftime("%d/%m/%Y")
    elements.append(Paragraph(f"LISTA DE FREQUÊNCIA", title_style))
    elements.append(Paragraph(f"<i>Gerado em {current_date}</i>", ParagraphStyle(
        name='date_style', parent=normal_style, alignment=TA_CENTER, fontSize=8, textColor=colors.gray
    )))
    elements.append(Spacer(1, 10 * mm))
    
    # Workshop information in a visually appealing box
    workshop_info = [
        [Paragraph("<b>INFORMAÇÕES DA OFICINA</b>", ParagraphStyle(
            name='workshop_header_style', parent=heading_style, textColor=colors.white, alignment=TA_CENTER
        ))]
    ]
    
    workshop_info_table = Table(workshop_info, colWidths=[doc.width])
    workshop_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('ROUNDEDCORNERS', [5, 5, 5, 5]),
    ]))
    elements.append(workshop_info_table)
    elements.append(Spacer(1, 2 * mm))
    
    # Workshop details
    elements.append(Paragraph(f"<b>Título:</b> {oficina.titulo}", info_style))
    
    ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A'
    elements.append(Paragraph(f"<b>Ministrante:</b> {ministrante_nome}", info_style))
    
    elements.append(Paragraph(f"<b>Local:</b> {oficina.cidade}, {oficina.estado}", info_style))
    
    elements.append(Paragraph("<b>Carga Horária:</b> {0} horas".format(oficina.carga_horaria), info_style))
    
    # Dates and times
    if oficina.dias:
        elements.append(Paragraph("<b>Datas e Horários:</b>", info_style))
        
        dates_data = []
        for dia in oficina.dias:
            data_formatada = dia.data.strftime('%d/%m/%Y')
            horario = f"{dia.horario_inicio} às {dia.horario_fim}"
            dates_data.append([
                Paragraph(data_formatada, normal_style),
                Paragraph(horario, normal_style)
            ])
        
        if dates_data:
            dates_table = Table(dates_data, colWidths=[doc.width/2 - 10*mm, doc.width/2 - 10*mm])
            dates_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(dates_table)
    else:
        elements.append(Paragraph("<b>Datas:</b> Nenhuma data registrada", info_style))
    
    elements.append(Spacer(1, 15 * mm))
    
    # Attendance list header
    elements.append(Paragraph("LISTA DE PRESENÇA", heading_style))
    elements.append(Spacer(1, 5 * mm))
    
    # Attendance table with signature column
    table_data = [
        [
            Paragraph("<b>Nº</b>", normal_style),
            Paragraph("<b>Nome Completo</b>", normal_style),
            Paragraph("<b>Assinatura</b>", normal_style)
        ]
    ]
    
    # Add rows for each participant
    for i, inscricao in enumerate(oficina.inscritos, 1):
        table_data.append([
            Paragraph(str(i), normal_style),
            Paragraph(inscricao.usuario.nome, normal_style),
            ""  # Signature space
        ])
    
    # Add empty rows if needed (to ensure at least 15 rows)
    current_rows = len(table_data) - 1  # Exclude header
    if current_rows < 15:
        for i in range(current_rows + 1, 16):
            table_data.append([
                Paragraph(str(i), normal_style),
                "",  # Empty name
                ""   # Signature space
            ])
    
    # Create the table with appropriate width distribution
    table = Table(table_data, colWidths=[15*mm, 85*mm, 70*mm])
    
    # Apply styles to the table
    table.setStyle(TableStyle([
        # Header row styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        
        # Data rows styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Center the numbers
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Left-align the names
        
        # Grid styling
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#023E8A")),
        
        # Alternating row colors for better readability
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
        
        # Cell padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        
        # Line height for signature spaces
        ('LINEBELOW', (2, 1), (2, -1), 0.5, colors.HexColor("#AAAAAA")),
    ]))
    
    elements.append(table)
    
    # Footer with signature fields
    elements.append(Spacer(1, 30 * mm))
    
    # Create signature lines
    signature_data = [
        [
            Paragraph("_______________________________", ParagraphStyle(name="signature_line", parent=normal_style, alignment=TA_CENTER)),
            "",
            Paragraph("_______________________________", ParagraphStyle(name="signature_line", parent=normal_style, alignment=TA_CENTER))
        ],
        [
            Paragraph("Ministrante", ParagraphStyle(name="signature_label", parent=normal_style, alignment=TA_CENTER)),
            "",
            Paragraph("Coordenador", ParagraphStyle(name="signature_label", parent=normal_style, alignment=TA_CENTER))
        ]
    ]
    
    signature_table = Table(signature_data, colWidths=[doc.width/3, doc.width/3, doc.width/3])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(signature_table)
    
    # Add page numbers
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        text = f"Página {page_num}"
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(
            doc.pagesize[0] - doc.rightMargin, 
            doc.bottomMargin/2, 
            text
        )
    
    # Build the PDF with page numbers
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)    
    

def gerar_pdf_inscritos_pdf(oficina_id):
    """
    Gera um PDF com a lista de inscritos para uma oficina específica,
    com layout moderno e organizado.
    """
    # Importações necessárias
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.platypus import PageBreak, Flowable
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    import os
    from flask import send_file
    from datetime import datetime
    
    # Busca a oficina no banco de dados
    oficina = Oficina.query.get_or_404(oficina_id)
    
    # Preparar o diretório para salvar o PDF
    pdf_filename = f"inscritos_oficina_{oficina.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    diretorio = os.path.join("static", "comprovantes")
    os.makedirs(diretorio, exist_ok=True)
    pdf_path = os.path.join(diretorio, pdf_filename)

    # Configurar estilos personalizados
    styles = getSampleStyleSheet()
    
    # Estilo de título modernizado
    title_style = ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#023E8A')
    )
    
    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        name='CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_LEFT,
        spaceAfter=3 * mm,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0077B6')
    )
    
    # Estilo para texto normal
    normal_style = ParagraphStyle(
        name='CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=2 * mm,
        fontName='Helvetica'
    )
    
    # Estilo para texto em tabelas (para permitir quebra de linha)
    table_text_style = ParagraphStyle(
        name='TableText',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        leading=12,
        wordWrap='CJK'
    )
    
    # Estilo para rodapé
    footer_style = ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.darkgrey,
        alignment=TA_CENTER
    )

    # Crie uma classe personalizada para linha horizontal
    class HorizontalLine(Flowable):
        def __init__(self, width, thickness=1):
            Flowable.__init__(self)
            self.width = width
            self.thickness = thickness
        
        def draw(self):
            self.canv.setStrokeColor(colors.HexColor('#0077B6'))
            self.canv.setLineWidth(self.thickness)
            self.canv.line(0, 0, self.width, 0)
    
    # Criar um documento PDF
    doc = SimpleDocTemplate(
        pdf_path, 
        pagesize=A4,
        leftMargin=2.5*cm, 
        rightMargin=2.5*cm, 
        topMargin=2*cm, 
        bottomMargin=2*cm
    )
    
    # Lista para armazenar elementos do PDF
    elements = []
    
    # Verificar se há um logo personalizado para o cliente
    # Se a oficina estiver associada a um cliente e o cliente tiver um logo
    logo_path = None
    if oficina.cliente_id:
        cliente = Cliente.query.get(oficina.cliente_id)
        if cliente and hasattr(cliente, 'logo_certificado') and cliente.logo_certificado:
            logo_path = cliente.logo_certificado
    
    # Se encontrou logo personalizado, adiciona ao PDF
    if logo_path and os.path.exists(logo_path):
        logo = Image(logo_path)
        logo.drawHeight = 2 * cm
        logo.drawWidth = 5 * cm
        elements.append(logo)
        elements.append(Spacer(1, 5 * mm))
    
    # Título principal
    elements.append(Paragraph(f"Lista de Inscritos", title_style))
    elements.append(Paragraph(f"{oficina.titulo}", subtitle_style))
    elements.append(HorizontalLine(doc.width))
    elements.append(Spacer(1, 5 * mm))
    
    # Informações da oficina em formato mais elegante
    elements.append(Paragraph("<b>Detalhes da Oficina</b>", subtitle_style))
    
    ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'Não atribuído'
    elements.append(Paragraph(f"<b>Ministrante:</b> {ministrante_nome}", normal_style))
    elements.append(Paragraph(f"<b>Local:</b> {oficina.cidade}, {oficina.estado}", normal_style))
    elements.append(Paragraph(f"<b>Carga Horária:</b> {oficina.carga_horaria} horas", normal_style))
    
    # Criar uma tabela para as datas e horários se houver dados
    if oficina.dias and len(oficina.dias) > 0:
        elements.append(Paragraph("<b>Datas e Horários:</b>", normal_style))
        
        date_data = [["Data", "Início", "Término"]]
        for dia in oficina.dias:
            data_formatada = dia.data.strftime('%d/%m/%Y')
            # Convertendo os valores para Paragraph para permitir quebra de linha
            date_data.append([
                Paragraph(data_formatada, table_text_style),
                Paragraph(dia.horario_inicio, table_text_style),
                Paragraph(dia.horario_fim, table_text_style)
            ])
        
        date_table = Table(date_data, colWidths=[doc.width * 0.4, doc.width * 0.3, doc.width * 0.3])
        date_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EBF2FA')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#023E8A')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            # Define que o texto pode quebrar dentro das células
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        elements.append(date_table)
    else:
        elements.append(Paragraph("<b>Datas:</b> Nenhuma data registrada", normal_style))
    
    elements.append(Spacer(1, 8 * mm))
    elements.append(HorizontalLine(doc.width))
    elements.append(Spacer(1, 8 * mm))
    
    # Adicionar contador de inscritos
    total_inscritos = len(oficina.inscritos) if oficina.inscritos else 0
    elements.append(Paragraph(f"<b>Total de Inscritos:</b> {total_inscritos}", subtitle_style))
    elements.append(Spacer(1, 5 * mm))
    
    # Tabela de inscritos com estilo moderno
    if oficina.inscritos and len(oficina.inscritos) > 0:
        table_data = [["#", "Nome", "CPF", "E-mail"]]
        
        for idx, inscricao in enumerate(oficina.inscritos, 1):
            # Verifica se é um objeto mapeado ou um objeto de modelo regular
            if hasattr(inscricao, 'usuario'):
                nome = inscricao.usuario.nome
                cpf = inscricao.usuario.cpf
                email = inscricao.usuario.email
            else:
                nome = inscricao.get('nome', 'N/A')
                cpf = inscricao.get('cpf', 'N/A')
                email = inscricao.get('email', 'N/A')
                
            # Formatação de CPF se necessário (adicionar pontos e traço)
            if cpf and len(cpf) == 11 and cpf.isdigit():
                cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
                
            # Usando Paragraph para permitir quebra de linha em cada coluna
            table_data.append([
                Paragraph(str(idx), table_text_style),
                Paragraph(nome, table_text_style),
                Paragraph(cpf, table_text_style),
                Paragraph(email, table_text_style)
            ])
        
        # Definir larguras das colunas para melhor distribuição
        col_widths = [doc.width * 0.05, doc.width * 0.35, doc.width * 0.25, doc.width * 0.35]
        
        # Criar tabela com estilo moderno
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            # Cabeçalho com cor de fundo
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#023E8A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Centraliza a coluna de números
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),    # Alinha nomes à esquerda
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),  # Centraliza CPFs
            ('ALIGN', (3, 0), (3, -1), 'LEFT'),    # Alinha e-mails à esquerda
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            # Linhas alternadas para melhor legibilidade
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            # Bordas mais sutis
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            # Configuração para permitir quebra de linha
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("Não há inscritos nesta oficina.", normal_style))
    
    # Adiciona espaço para assinatura
    elements.append(Spacer(1, 2 * cm))
    elements.append(HorizontalLine(doc.width * 0.4))
    elements.append(Paragraph("Assinatura do Coordenador", footer_style))
    
    # Adiciona rodapé com data de geração
    elements.append(Spacer(1, 2 * cm))
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")
    elements.append(HorizontalLine(doc.width))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(f"Documento gerado em {current_date} | AppFiber", footer_style))
    
    # Construir o PDF
    doc.build(elements)
    
    # Retorna o arquivo para download
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)

    
def gerar_lista_frequencia(oficina_id, pdf_path=None):
    """
    Generates a modern and professional attendance list PDF for a workshop.
    
    Args:
        oficina_id: The ID of the workshop
        pdf_path: The file path where the PDF will be saved (optional)
    """
    # Importações necessárias
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    import os
    from datetime import datetime
    from flask import send_file
    from models import Oficina, Inscricao

    # Obter a oficina real pelo ID
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        raise ValueError("Oficina não encontrada!")

    # Se pdf_path não for fornecido, gere um caminho padrão
    if pdf_path is None:
        import tempfile
        pdf_path = os.path.join(tempfile.gettempdir(), f"lista_frequencia_{oficina_id}.pdf")

    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        textColor=colors.HexColor("#023E8A"),
        spaceAfter=10,
        alignment=TA_CENTER
    )

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []

    # Cabeçalho
    elements.append(Paragraph("LISTA DE FREQUÊNCIA", title_style))
    elements.append(Paragraph(f"<i>{oficina.titulo}</i>", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Dados da oficina
    ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A'
    elements.append(Paragraph(f"<b>Ministrante:</b> {ministrante_nome}", styles['Normal']))
    elements.append(Paragraph(f"<b>Local:</b> {oficina.cidade}, {oficina.estado}", styles['Normal']))
    elements.append(Paragraph(f"<b>Carga Horária:</b> {oficina.carga_horaria} horas", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Tabela de frequência
    table_data = [["Nº", "Nome Completo", "Assinatura"]]

    # Buscando participantes reais inscritos
    inscricoes = Inscricao.query.filter_by(oficina_id=oficina_id).all()

    for i, inscricao in enumerate(inscricoes, 1):
        nome_participante = inscricao.usuario.nome if inscricao.usuario else 'N/A'
        # Observe que usamos Paragraph para permitir a quebra de linha no nome
        table_data.append([
            Paragraph(str(i), styles['Normal']),
            Paragraph(nome_participante, styles['Normal']),
            ""
        ])

    table = Table(table_data, colWidths=[30*mm, 100*mm, 60*mm])

    # Aplica estilos, incluindo WORDWRAP
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Rodapé para assinaturas
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("________________________", styles['Normal']))
    elements.append(Paragraph("Ministrante", styles['Normal']))

    elements.append(Spacer(1, 48))
    elements.append(Paragraph("________________________", styles['Normal']))
    elements.append(Paragraph("Coordenador", styles['Normal']))

    # Gera PDF
    doc.build(elements)

    return send_file(pdf_path)


@_profile
def gerar_comprovante_pdf(usuario, oficina, inscricao):
    """
    Gera um comprovante de inscrição em PDF com design moderno e organizado.
    """
    # Configurar nomes e caminhos de arquivo
    pdf_filename = f"comprovante_{usuario.id}_{oficina.id}.pdf"
    pdf_path = os.path.join("static/comprovantes", pdf_filename)
    os.makedirs("static/comprovantes", exist_ok=True)

    # Gera o QR Code da inscrição
    qr_path = gerar_qr_code_inscricao(inscricao.qr_code_token)
    
    # Inicializa o PDF com a página em portrait
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    
    # ----- DESIGN DO CABEÇALHO -----
    
    # Gradiente de fundo do cabeçalho (de azul escuro para azul médio)
    # Método manual para criar um efeito de gradiente
    header_height = 120
    gradient_steps = 40
    step_height = header_height / gradient_steps
    
    for i in range(gradient_steps):
        # Interpolação de cores: de #023E8A (azul escuro) para #0077B6 (azul médio)
        r1, g1, b1 = 0.01, 0.24, 0.54  # #023E8A
        r2, g2, b2 = 0.00, 0.47, 0.71  # #0077B6
        
        # Calcular cor intermediária
        ratio = i / gradient_steps
        r = r1 + (r2 - r1) * ratio
        g = g1 + (g2 - g1) * ratio
        b = b1 + (b2 - b1) * ratio
        
        y_pos = height - (i * step_height)
        c.setFillColorRGB(r, g, b)
        c.rect(0, y_pos - step_height, width, step_height, fill=True, stroke=False)
    
    # Logo ou texto estilizado (lado esquerdo)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, height - 40, "AppFiber")
    
    # Linha fina decorativa 
    c.setStrokeColor(colors.white)
    c.setLineWidth(1)
    c.line(1 * inch, height - 45, 2 * inch, height - 45)
    
    # Título centralizado
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 70, "Comprovante de Inscrição")
    
    # Data no cabeçalho (lado direito)
    from datetime import datetime
    data_atual = datetime.now().strftime("%d/%m/%Y")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 1 * inch, height - 40, f"Emitido em: {data_atual}")
    
    # ----- CORPO DO DOCUMENTO -----
    
    # Fundo do corpo com cor suave
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height - header_height, fill=True, stroke=False)
    
    # Área de informações principais com borda arredondada
    info_box_y = height - 200
    info_box_height = 150
    
    # Borda e fundo do box de informações
    c.setFillColor(colors.whitesmoke)
    c.setStrokeColor(colors.lightgrey)
    c.roundRect(0.8 * inch, info_box_y - info_box_height, width - 1.6 * inch, 
               info_box_height, 10, fill=1, stroke=1)
    
    # Título da seção
    c.setFillColor(colors.HexColor("#0077B6"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, info_box_y - 25, "Informações do Participante")
    
    # Linhas de informação com ícones simulados
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 12)
    
    # Posição inicial do texto
    y_position = info_box_y - 50
    line_spacing = 22
    
    # Informações com pequenos marcadores
    infos = [
        (f"Nome: {usuario.nome}", "👤"),
        (f"CPF: {usuario.cpf}", "🆔"),
        (f"E-mail: {usuario.email}", "✉️"),
        (f"Oficina: {oficina.titulo}", "📚")
    ]
    
    for texto, icone in infos:
        c.drawString(1.1 * inch, y_position, f"{icone} {texto}")
        y_position -= line_spacing
    
    # ----- SEÇÃO DE DETALHES DA OFICINA -----
    
    details_y = info_box_y - info_box_height - 20
    
    # Título da seção de detalhes
    c.setFillColor(colors.HexColor("#0077B6"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, details_y, "Detalhes da Oficina")
    
    # Detalhes da oficina
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 12)
    
    # Verifica se existem dias associados à oficina
    if hasattr(oficina, 'dias') and oficina.dias:
        y_position = details_y - 25
        c.drawString(1.1 * inch, y_position, "📅 Datas e Horários:")
        
        # Lista cada dia da oficina
        for i, dia in enumerate(oficina.dias):
            if i < 3:  # Limita para mostrar apenas 3 datas para não sobrecarregar
                data_formatada = dia.data.strftime('%d/%m/%Y')
                c.drawString(1.3 * inch, y_position - ((i+1) * line_spacing), 
                           f"{data_formatada} | {dia.horario_inicio} às {dia.horario_fim}")
            elif i == 3:
                c.drawString(1.3 * inch, y_position - ((i+1) * line_spacing), "...")
                break
    
    # ----- QR CODE -----
    
    # Box para QR Code com sombra suave
    qr_size = 120
    qr_x = width - qr_size - 1.2 * inch
    qr_y = height - 220
    
    # Sombra (um retângulo cinza levemente deslocado)
    c.setFillColor(colors.grey)
    c.setFillAlpha(0.3)  # Transparência
    c.roundRect(qr_x + 3, qr_y - 3, qr_size, qr_size, 5, fill=True, stroke=False)
    
    # Restaura a transparência
    c.setFillAlpha(1)
    
    # Fundo branco para o QR
    c.setFillColor(colors.white)
    c.roundRect(qr_x, qr_y, qr_size, qr_size, 5, fill=True, stroke=False)
    
    # Desenhando o QR Code
    qr_img = ImageReader(qr_path)
    c.drawImage(qr_img, qr_x + 10, qr_y + 10, width=qr_size - 20, height=qr_size - 20)
    
    # Legenda do QR
    c.setFillColor(colors.dimgrey)
    c.setFont("Helvetica", 10)
    c.drawCentredString(qr_x + qr_size/2, qr_y - 15, "Escaneie para check-in")
    
    # ----- RODAPÉ -----
    
    # Linha divisória
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(1)
    c.line(1 * inch, 1.2 * inch, width - 1 * inch, 1.2 * inch)
    
    # Texto de validação
    c.setFillColor(colors.grey)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 1 * inch, 
                      f"Este comprovante é válido para a oficina '{oficina.titulo}'")
    c.drawCentredString(width / 2, 0.8 * inch, 
                      f"ID do Participante: {usuario.id} | ID da Inscrição: {inscricao.id}")
    
    # Rodapé com informações do sistema
    c.setFillColor(colors.dimgrey)
    c.drawCentredString(width / 2, 0.5 * inch, "AppFiber - Sistema Integrado de Gerenciamento de Eventos")
    
    # Finaliza o PDF
    c.save()
    
    return pdf_path



@login_required
def gerar_certificados(oficina_id):
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Apenas administradores podem gerar certificados.", "danger")
        

    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash("Oficina não encontrada!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    inscritos = oficina.inscritos
    if not inscritos:
        flash("Não há inscritos nesta oficina para gerar certificados!", "warning")
        return redirect(url_for(endpoints.DASHBOARD))

    pdf_path = f"static/certificados/certificados_oficina_{oficina.id}.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Agora chama a função ajustada
    gerar_certificados_pdf(oficina, inscritos, pdf_path)

    flash("Certificados gerados com sucesso!", "success")
    return send_file(pdf_path, as_attachment=True)

def gerar_lista_frequencia(oficina_id, pdf_path=None):
    """
    Generates a modern and professional attendance list PDF for a workshop.
    
    Args:
        oficina_id: The ID of the workshop
        pdf_path: The file path where the PDF will be saved (optional)
    """
    # Importações necessárias
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    import os
    from datetime import datetime
    from flask import send_file
    from models import Oficina, Inscricao

    # Obter a oficina real pelo ID
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        raise ValueError("Oficina não encontrada!")

    # Se pdf_path não for fornecido, gere um caminho padrão
    if pdf_path is None:
        import tempfile
        pdf_path = os.path.join(tempfile.gettempdir(), f"lista_frequencia_{oficina_id}.pdf")

    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        textColor=colors.HexColor("#023E8A"),
        spaceAfter=10,
        alignment=TA_CENTER
    )

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []

    # Cabeçalho
    elements.append(Paragraph("LISTA DE FREQUÊNCIA", title_style))
    elements.append(Paragraph(f"<i>{oficina.titulo}</i>", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Dados da oficina
    ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A'
    elements.append(Paragraph(f"<b>Ministrante:</b> {ministrante_nome}", styles['Normal']))
    elements.append(Paragraph(f"<b>Local:</b> {oficina.cidade}, {oficina.estado}", styles['Normal']))
    elements.append(Paragraph(f"<b>Carga Horária:</b> {oficina.carga_horaria} horas", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Tabela de frequência
    table_data = [["Nº", "Nome Completo", "Assinatura"]]

    # Buscando participantes reais inscritos
    inscricoes = Inscricao.query.filter_by(oficina_id=oficina_id).all()

    for i, inscricao in enumerate(inscricoes, 1):
        nome_participante = inscricao.usuario.nome if inscricao.usuario else 'N/A'
        # Observe que usamos Paragraph para permitir a quebra de linha no nome
        table_data.append([
            Paragraph(str(i), styles['Normal']),
            Paragraph(nome_participante, styles['Normal']),
            ""
        ])

    table = Table(table_data, colWidths=[30*mm, 100*mm, 60*mm])

    # Aplica estilos, incluindo WORDWRAP
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Rodapé para assinaturas
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("________________________", styles['Normal']))
    elements.append(Paragraph("Ministrante", styles['Normal']))

    elements.append(Spacer(1, 48))
    elements.append(Paragraph("________________________", styles['Normal']))
    elements.append(Paragraph("Coordenador", styles['Normal']))

    # Gera PDF
    doc.build(elements)

    return send_file(pdf_path)



def gerar_certificados(oficina_id):
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Apenas administradores podem gerar certificados.", "danger")
        

    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash("Oficina não encontrada!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    inscritos = oficina.inscritos
    if not inscritos:
        flash("Não há inscritos nesta oficina para gerar certificados!", "warning")
        return redirect(url_for(endpoints.DASHBOARD))

    pdf_path = f"static/certificados/certificados_oficina_{oficina.id}.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Agora chama a função ajustada
    gerar_certificados_pdf(oficina, inscritos, pdf_path)

    flash("Certificados gerados com sucesso!", "success")
    return send_file(pdf_path, as_attachment=True)

def gerar_pdf_feedback(oficina, feedbacks, pdf_path):
    """
    Gera um PDF elegante com os feedbacks de uma oficina.
    
    Args:
        oficina: Objeto da oficina com informações como título
        feedbacks: Lista de objetos de feedback contendo avaliações e comentários
        pdf_path: Caminho onde o PDF será salvo
    """
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, SimpleDocTemplate, PageBreak, Image
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from datetime import datetime
    import pytz
    import os
    
    # Função para converter um datetime para o fuso de Brasília
    def convert_to_brasilia(dt):
        brasilia_tz = pytz.timezone("America/Sao_Paulo")
        # Se o datetime não for "aware", assume-se que está em UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.utc)
        return dt.astimezone(brasilia_tz)
    
    # Criar estilos personalizados
    styles = getSampleStyleSheet()
    
    # Título com estilo moderno
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=24,
        fontName='Helvetica-Bold',
        alignment=1,  # Centralizado
        spaceAfter=20,
        textColor=colors.HexColor('#1A365D')  # Azul escuro elegante
    )
    
    # Estilo para o subtítulo
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=16,
        fontName='Helvetica-Bold',
        alignment=1,
        spaceAfter=15,
        textColor=colors.HexColor('#2A4365')  # Azul médio
    )
    
    # Estilo para o texto normal
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        fontName='Helvetica'
    )
    
    # Estilo para o cabeçalho da tabela
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading4'],
        fontSize=12,
        fontName='Helvetica-Bold',
        alignment=1,
        textColor=colors.white,
        leading=14
    )
    
    # Estilo para o rodapé
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Oblique',
        textColor=colors.HexColor('#4A5568'),  # Cinza escuro
        alignment=1
    )
    
    # Estilo para comentários
    comment_style = ParagraphStyle(
        'CommentStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        fontName='Helvetica',
        firstLineIndent=0,
        spaceBefore=3,
        spaceAfter=3
    )
    
    # Cria o documento em modo paisagem com margens aprimoradas
    doc = SimpleDocTemplate(
        pdf_path, 
        pagesize=landscape(letter), 
        leftMargin=0.75*inch, 
        rightMargin=0.75*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    available_width = doc.width  # largura disponível após as margens
    
    elements = []
    
    # Adicionar logotipo ou imagem header (opcional)
    logo_path = os.path.join("static", "logo.png")
    if os.path.exists(logo_path):
        # Adiciona um espaço antes do logo
        elements.append(Spacer(1, 0.2 * inch))
        
        # Centraliza o logo
        logo = Image(logo_path, width=1.5*inch, height=0.75*inch)
        elements.append(logo)
        
        # Adiciona um espaço após o logo
        elements.append(Spacer(1, 0.3 * inch))
    
    # Título principal
    elements.append(Paragraph(f"Relatório de Feedback", title_style))
    
    # Subtítulo com informações da oficina
    elements.append(Paragraph(f"Oficina: {oficina.titulo}", subtitle_style))
    
    # Adicionar informações da data de geração
    now = convert_to_brasilia(datetime.utcnow())
    elements.append(Paragraph(f"Gerado em: {now.strftime('%d/%m/%Y às %H:%M')}", normal_style))
    
    # Informações gerais (pode-se adicionar ministrate, datas, etc.)
    ministrante_nome = oficina.ministrante_obj.nome if hasattr(oficina, 'ministrante_obj') and oficina.ministrante_obj else 'N/A'
    elements.append(Paragraph(f"Ministrante: {ministrante_nome}", normal_style))
    
    # Verificar se oficina tem atributo 'cidade' e 'estado'
    if hasattr(oficina, 'cidade') and hasattr(oficina, 'estado'):
        elements.append(Paragraph(f"Local: {oficina.cidade}, {oficina.estado}", normal_style))
    
    # Calcular estatísticas de avaliação
    if feedbacks:
        total_ratings = len(feedbacks)
        avg_rating = sum(fb.rating for fb in feedbacks) / total_ratings if total_ratings > 0 else 0
        elements.append(Paragraph(f"Avaliação média: {avg_rating:.1f}/5.0 ({total_ratings} avaliações)", normal_style))
    
    # Adicionar espaço antes da tabela
    elements.append(Spacer(1, 0.4 * inch))
    
    # Linha decorativa antes da tabela
    elements.append(Table([['']], colWidths=[doc.width], 
                          style=TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#3182CE'))])))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Título da seção de feedbacks
    elements.append(Paragraph("Detalhes dos Feedbacks", subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Cabeçalho da tabela com Paragraph para melhor formatação
    header = [
        Paragraph("Usuário", header_style),
        Paragraph("Avaliação", header_style),
        Paragraph("Comentário", header_style),
        Paragraph("Data", header_style)
    ]
    table_data = [header]
    
    # Prepara os dados da tabela convertendo os horários para o fuso local
    for fb in feedbacks:
        # Criar string de estrelas
        filled_star = "★"  # Estrela preenchida
        empty_star = "☆"   # Estrela vazia
        rating_str = filled_star * fb.rating + empty_star * (5 - fb.rating)
        
        # Formatar data local
        dt_local = convert_to_brasilia(fb.created_at)
        data_str = dt_local.strftime('%d/%m/%Y %H:%M')
        
        # Determinar o nome do autor
        nome_autor = fb.usuario.nome if hasattr(fb, 'usuario') and fb.usuario is not None else (
                     fb.ministrante.nome if hasattr(fb, 'ministrante') and fb.ministrante is not None else "Desconhecido")
        
        # Garante que o comentário não seja None
        comentario_text = fb.comentario or "Sem comentários adicionais."
        
        # Utiliza Paragraph para permitir quebra de linha em comentários longos
        comentario_paragraph = Paragraph(comentario_text, comment_style)
        
        row = [
            Paragraph(nome_autor, normal_style),
            Paragraph(rating_str, normal_style),
            comentario_paragraph,
            Paragraph(data_str, normal_style)
        ]
        table_data.append(row)
    
    # Cria o documento em modo paisagem com margens aprimoradas
    doc = SimpleDocTemplate(
        pdf_path, 
        pagesize=landscape(letter), 
        leftMargin=0.75*inch, 
        rightMargin=0.75*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    available_width = doc.width  # largura disponível após as margens
    
    # Define as larguras das colunas em porcentagem da largura disponível
    col_widths = [
        available_width * 0.20,  # Usuário
        available_width * 0.15,  # Avaliação
        available_width * 0.45,  # Comentário
        available_width * 0.20   # Data
    ]
    
    # Cria e estiliza a tabela
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Cores suaves e modernas
    header_bg_color = colors.HexColor('#2C5282')  # Azul escuro
    alt_row_color = colors.HexColor('#EBF8FF')    # Azul bem claro
    grid_color = colors.HexColor('#CBD5E0')       # Cinza claro
    
    table.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), header_bg_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Linhas alternadas para facilitar a leitura
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, alt_row_color]),
        
        # Grade fina e elegante
        ('GRID', (0, 0), (-1, -1), 0.5, grid_color),
        
        # Alinhamento
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),       # Cabeçalho centralizado
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),       # Coluna de avaliação centralizada
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),         # Coluna de usuários à esquerda
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),       # Coluna de datas centralizada
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),     # Alinhamento vertical no meio
        
        # Espaçamento interno
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
    ]))
    
    elements.append(table)
    
    # Adiciona espaço antes do rodapé
    elements.append(Spacer(1, 0.4 * inch))
    
    # Linha decorativa antes do rodapé
    elements.append(Table([['']], colWidths=[doc.width], 
                          style=TableStyle([('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor('#CBD5E0'))])))
    
    # Adiciona espaço após a linha
    elements.append(Spacer(1, 0.2 * inch))
    
    # Rodapé com horário local e informações adicionais
    footer_text = "Este relatório é um documento confidencial e de uso interno. "
    footer_text += f"Gerado via AppFiber em {now.strftime('%d/%m/%Y às %H:%M')}."
    elements.append(Paragraph(footer_text, footer_style))
    
    # Construir o PDF
    doc.build(elements)



def gerar_pdf_feedback_route(oficina_id):
    if current_user.tipo != 'admin' and current_user.tipo != 'cliente':
        flash('Acesso Autorizado!', 'danger')
        
    oficina = Oficina.query.get_or_404(oficina_id)
    
    # Replicar a lógica de filtragem usada na rota feedback_oficina
    query = Feedback.query.filter(Feedback.oficina_id == oficina_id)
    tipo = request.args.get('tipo')
    if tipo == 'usuario':
        query = query.filter(Feedback.usuario_id.isnot(None))
    elif tipo == 'ministrante':
        query = query.filter(Feedback.ministrante_id.isnot(None))
    estrelas = request.args.get('estrelas')
    if estrelas and estrelas.isdigit():
        query = query.filter(Feedback.rating == int(estrelas))
    
    feedbacks = query.order_by(Feedback.created_at.desc()).all()
    
    pdf_folder = os.path.join("static", "feedback_pdfs")
    os.makedirs(pdf_folder, exist_ok=True)
    pdf_filename = f"feedback_{oficina.id}.pdf"
    pdf_path = os.path.join(pdf_folder, pdf_filename)
    gerar_pdf_feedback(oficina, feedbacks, pdf_path)
    return send_file(pdf_path, as_attachment=True)


def gerar_pdf_checkins_qr():
    import os
    import pytz
    from datetime import datetime
    from collections import defaultdict
    from flask import flash, redirect, url_for, send_file
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from models import Checkin, Usuario, Oficina
    from extensions import db
    from flask_login import current_user
    from sqlalchemy import or_

    logger.info(
        "\n📥 DEBUG: Cliente logado: %s (%s)", current_user.id, current_user.nome
    )

    checkins_qr = (
        Checkin.query
        .outerjoin(Checkin.oficina)
        .outerjoin(Checkin.usuario)
        .filter(
            Checkin.palavra_chave.in_(['QR-AUTO', 'QR-EVENTO', 'QR-OFICINA']),
            or_(
                Usuario.cliente_id == current_user.id,
                Oficina.cliente_id == current_user.id,
                Checkin.cliente_id == current_user.id
            )
        )
        .order_by(Checkin.data_hora.desc())
        .all()
    )

    logger.info("📊 DEBUG: Total de check-ins encontrados: %s", len(checkins_qr))
    for i, ck in enumerate(checkins_qr, start=1):
        logger.info(
            " - Checkin %s: Usuario=%s | Email=%s | Palavra=%s | Oficina=%s | ClienteID=%s",
            i,
            ck.usuario.nome if ck.usuario else "N/A",
            ck.usuario.email if ck.usuario else "N/A",
            ck.palavra_chave,
            "N/A" if not ck.oficina else ck.oficina.titulo,
            ck.cliente_id,
        )

    if not checkins_qr:
        flash("Não há check-ins via QR Code para gerar o relatório.", "warning")
        return redirect(url_for(endpoints.DASHBOARD))

    # (continua com sua lógica atual do PDF sem alterações)
    # 2. Configuração do documento
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"checkins_qr_{current_time}.pdf"
    pdf_dir = os.path.join("static", "relatorios")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_filename)

    # 3. Definição de estilos personalizados
    styles = getSampleStyleSheet()
    
    # Estilo para o título principal
    title_style = ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        textColor=colors.HexColor("#023E8A"),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    # Estilo para subtítulos (oficinas)
    subtitle_style = ParagraphStyle(
        name='CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor("#1A75CF"),
        spaceBefore=15,
        spaceAfter=10,
        borderWidth=1,
        borderColor=colors.HexColor("#1A75CF"),
        borderPadding=5,
        borderRadius=3
    )
    
    # Estilo para o rodapé
    footer_style = ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_RIGHT
    )

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=landscape(A4),
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=20*mm,
        bottomMargin=15*mm
    )
    elements = []

    # 5. Cabeçalho do relatório
    elements.append(Paragraph("Relatório de Check-ins via QR Code", title_style))
    elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", footer_style))
    elements.append(Spacer(1, 10*mm))

    # 6. Configuração do fuso horário (Brasil)
    brasilia_tz = pytz.timezone("America/Sao_Paulo")
    
    def convert_to_brasilia(dt):
        """Converte datetime para horário de Brasília."""
        if dt is None:
            return None
        # Se o datetime não for "aware", assume-se que está em UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.utc)
        return dt.astimezone(brasilia_tz)

    # 7. Agrupamento dos check-ins por oficina ou evento
    grupos_checkins = defaultdict(list)
    for checkin in checkins_qr:
        if checkin.oficina:
            grupo_titulo = checkin.oficina.titulo
        elif checkin.evento:
            grupo_titulo = checkin.evento.nome
        else:
            grupo_titulo = "Atividade não especificada"
        grupos_checkins[grupo_titulo].append(checkin)

    # 8. Definição do estilo de tabela
    table_style = TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8ecde6")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Corpo da tabela
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        
        # Linhas zebradas
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
        
        # Repetir cabeçalho em novas páginas
        ('REPEATROWS', (0, 0), (0, 0)),
        
        # Habilitar quebra de linha
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ])

    # 9. Gerar tabelas para cada grupo
    total_checkins = 0

    for grupo_titulo, checkins in grupos_checkins.items():
        total_grupo = len(checkins)
        total_checkins += total_grupo

        # Adicionar subtítulo do grupo
        elements.append(Paragraph(f"Atividade: {grupo_titulo} ({total_grupo} check-ins)", subtitle_style))
        
        # Preparar dados da tabela
        # Usamos Paragraph para cada célula, o que permite o WORDWRAP aplicado acima.
        table_data = [[
            Paragraph("Nome do Participante", styles["Normal"]),
            Paragraph("E-mail", styles["Normal"]),
            Paragraph("Turno", styles["Normal"]),
            Paragraph("Data/Hora do Check-in", styles["Normal"])
        ]]
        
        for ck in checkins:
            usuario = ck.usuario
            nome = usuario.nome if usuario else "N/A"
            email = usuario.email if usuario else "N/A"
            
            # Converter para horário de Brasília
            dt_local = convert_to_brasilia(ck.data_hora)
            data_str = dt_local.strftime('%d/%m/%Y %H:%M') if dt_local else "N/A"
            
            turno = determinar_turno(ck.data_hora)
            table_data.append([
                Paragraph(nome, styles["Normal"]),
                Paragraph(email, styles["Normal"]),
                Paragraph(turno, styles["Normal"]),
                Paragraph(data_str, styles["Normal"])
            ])
        
        # Definir larguras das colunas
        col_widths = [
            doc.width * 0.30,
            doc.width * 0.30,
            doc.width * 0.20,
            doc.width * 0.20
        ]
        
        table = LongTable(table_data, colWidths=col_widths)
        table.setStyle(table_style)
        elements.append(table)
        elements.append(Spacer(1, 8*mm))

    # 10. Resumo final
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph(f"Total de check-ins: {total_checkins}", styles["Heading3"]))
    
    # 11. Rodapé com informações do sistema
    footer_text = f"Documento gerado pelo sistema AppFiber em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
    elements.append(Spacer(1, 20*mm))
    elements.append(Paragraph(footer_text, footer_style))

    # 12. Gerar o PDF
    doc.build(elements)
    
    # 13. Retornar o arquivo para download
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def gerar_pdf_respostas(formulario_id):
    """
    Gera um PDF formatado e organizado das respostas de um formulário específico.
    
    Args:
        formulario_id: ID do formulário para buscar as respostas
        
    Returns:
        Um arquivo PDF para download
    """
    # Importações necessárias
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import pytz
    from models import Formulario, RespostaFormulario
    import os
    from flask import send_file, current_app
    import time
    from datetime import datetime
    from models import Formulario, RespostaFormulario
    
    # Busca o formulário e as respostas
    formulario = Formulario.query.get_or_404(formulario_id)
    respostas = RespostaFormulario.query.filter_by(formulario_id=formulario.id).all()
    
    # Verifica se há respostas
    if not respostas:
        return None, "Não existem respostas para este formulário"

    # Define nome e caminho do arquivo PDF
    timestamp = int(time.time())
    pdf_filename = f"respostas_{formulario.id}_{timestamp}.pdf"
    pdf_folder = os.path.join(current_app.static_folder, "reports")
    os.makedirs(pdf_folder, exist_ok=True)
    pdf_path = os.path.join(pdf_folder, pdf_filename)
    
    # Configura o documento com margens adequadas
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
        title=f"Respostas - {formulario.nome}"
    )
    
    # Configuração de estilos customizados
    styles = getSampleStyleSheet()
    
    # Estilo para o título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor("#023E8A"),
        alignment=TA_CENTER
    )
    
    # Estilo para cabeçalhos
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.white,
        alignment=TA_LEFT
    )
    
    # Estilo para o conteúdo
    content_style = ParagraphStyle(
        'ContentStyle',
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=6
    )
    
    # Estilo para o rodapé
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_CENTER
    )

    # Lista para armazenar os elementos do PDF
    elements = []
    
    # Tenta adicionar um logo se existir
    logo_path = os.path.join(current_app.static_folder, "img", "logo.png")
    if os.path.exists(logo_path):
        # Configura o logo centralizado
        logo = Image(logo_path)
        logo.drawHeight = 0.8 * inch
        logo.drawWidth = 2 * inch
        elements.append(logo)
        elements.append(Spacer(1, 0.25 * inch))
    
    # Título do PDF
    title = Paragraph(f"Respostas do Formulário: {formulario.nome}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))
    
    # Adiciona informações sobre o formulário
    if formulario.descricao:
        desc = Paragraph(f"<i>{formulario.descricao}</i>", content_style)
        elements.append(desc)
        elements.append(Spacer(1, 0.2 * inch))
    
    # Data de geração do relatório
    report_date = Paragraph(
        f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
        content_style
    )
    elements.append(report_date)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Função para converter datetime para o horário de Brasília
    def convert_to_brasilia(dt):
        brasilia_tz = pytz.timezone("America/Sao_Paulo")
        # Se o datetime não for "aware", assume-se que está em UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.utc)
        return dt.astimezone(brasilia_tz)
    
    # Cria tabela
    data = []
    header = [
        Paragraph("<b>Participante</b>", header_style),
        Paragraph("<b>Data de Envio</b>", header_style),
        Paragraph("<b>Respostas</b>", header_style)
    ]
    data.append(header)
    
    # Preenche as linhas da tabela com cada resposta
    for resposta in respostas:
        # Informações do usuário
        usuario = resposta.usuario.nome if resposta.usuario else "N/A"
        
        # Conversão de data para horário local
        dt_local = convert_to_brasilia(resposta.data_submissao)
        data_envio = dt_local.strftime('%d/%m/%Y %H:%M')
        
        # Formatação do status, se disponível
        status_text = ""
        if hasattr(resposta, 'status_avaliacao') and resposta.status_avaliacao:
            status_color = {
                'Aprovada': '#28a745',
                'Aprovada com ressalvas': '#ffc107',
                'Negada': '#dc3545',
                'Não Avaliada': '#6c757d'
            }.get(resposta.status_avaliacao, '#6c757d')
            
            status_text = f"<br/><b>Status:</b> <font color='{status_color}'>{resposta.status_avaliacao}</font>"
        
        # Formatação das respostas com melhor estruturação
        resposta_text = f"<b>Respostas de {usuario}</b>{status_text}<br/><br/>"
        
        for campo in resposta.respostas_campos:
            valor = campo.valor if campo.valor else "N/A"
            
            # Se for caminho de arquivo, mostra apenas o nome do arquivo
            if campo.campo.tipo == 'file' and valor and '/' in valor:
                arquivo = valor.split('/')[-1]
                valor = f"<i>Arquivo: {arquivo}</i>"
                
            resposta_text += f"<b>{campo.campo.nome}:</b><br/>{valor}<br/><br/>"
        
        # Criação dos parágrafos para a tabela
        usuario_cell = Paragraph(f"<b>{usuario}</b>", content_style)
        data_cell = Paragraph(data_envio, content_style)
        resposta_cell = Paragraph(resposta_text, content_style)
        
        # Adiciona a linha à tabela
        data.append([usuario_cell, data_cell, resposta_cell])
    
    # Define a largura das colunas (distribuição percentual)
    available_width = doc.width
    col_widths = [
        available_width * 0.25,  # Nome (25%)
        available_width * 0.15,  # Data (15%)
        available_width * 0.60   # Respostas (60%)
    ]
    
    # Criação da tabela com os dados e larguras definidas
    table = Table(data, colWidths=col_widths, repeatRows=1)
    
    # Estilo da tabela
    table_style = TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        
        # Bordas externas da tabela
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        
        # Linhas horizontais mais finas
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Alinhamento do texto
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        
        # Configurações de padding
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        
        # Zebra striping para facilitar a leitura
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ])
    
    table.setStyle(table_style)
    elements.append(table)
    
    # Adicionando rodapé
    elements.append(Spacer(1, 0.5 * inch))
    footer = Paragraph(
        f"© {datetime.now().year} - Documento gerado pelo sistema AppFiber - Página 1",
        footer_style
    )
    elements.append(footer)
    
    # Constrói o PDF
    doc.build(
        elements,
        onFirstPage=lambda canvas, doc: add_page_number(canvas, doc, 1),
        onLaterPages=lambda canvas, doc: add_page_number(canvas, doc)
    )
    
    # Retorna o arquivo para download
    return send_file(pdf_path, as_attachment=True)

def add_page_number(canvas, doc, page_num=None):
    """
    Adiciona o número de página ao rodapé.
    
    Args:
        canvas: O canvas do ReportLab
        doc: O documento
        page_num: Número específico de página (opcional)
    """
    page = page_num if page_num else canvas._pageNumber
    text = f"© {datetime.now().year} - Documento gerado pelo sistema AppFiber - Página {page}"
    
    # Define estilo e posição
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    
    # Posiciona na parte inferior central
    text_width = canvas.stringWidth(text, "Helvetica", 8)
    x = (doc.pagesize[0] - text_width) / 2
    canvas.drawString(x, 20, text)
    canvas.restoreState()

from flask import request, send_file, redirect, url_for, flash
from io import BytesIO
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from flask_login import login_required, current_user
from models import Checkin, Evento, ConfiguracaoCliente
import unicodedata



def exportar_checkins_pdf_opcoes():
    from flask import request
    import unicodedata
    from io import BytesIO
    from datetime import datetime
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from models import Checkin, Evento, Oficina

    def normalizar(texto):
        return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8").strip()

    tipo = normalizar(request.args.get('tipo', '').upper())
    evento_id = request.args.get('evento_id')

    if not current_user.is_cliente():
        flash("Acesso negado.", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    # Query base
    base_query = Checkin.query.filter(Checkin.cliente_id == current_user.id)

    if evento_id and evento_id != 'todos':
        base_query = base_query.filter(Checkin.evento_id == int(evento_id))

    if tipo and tipo != 'TODOS':
        base_query = base_query.filter(Checkin.palavra_chave == tipo)

    checkins = base_query.order_by(Checkin.data_hora.desc()).all()

    if not checkins:
        flash("Nenhum check-in encontrado para os filtros aplicados.", "info")
        return redirect(url_for(endpoints.DASHBOARD))

    # Gerar PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Cores modernas
    azul_principal = colors.HexColor('#2196F3')
    azul_claro = colors.HexColor('#BBDEFB')
    cinza_escuro = colors.HexColor('#424242')
    cinza_claro = colors.HexColor('#EEEEEE')
    
    def adicionar_cabecalho_rodape(pagina, num_pagina, total_paginas):
        # Cabeçalho
        pagina.setFillColor(azul_principal)
        pagina.rect(0, height - 2*cm, width, 2*cm, fill=1)
        
        pagina.setFillColor(colors.white)
        pagina.setFont("Helvetica-Bold", 16)
        titulo_relatorio = "Relatório de Check-ins"
        if tipo != 'TODOS':
            titulo_relatorio += f" - {tipo}"
        pagina.drawCentredString(width/2, height - 1.2*cm, titulo_relatorio)
        
        pagina.setFont("Helvetica", 10)
        data_relatorio = f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        pagina.drawString(width - 5*cm, height - 1.7*cm, data_relatorio)
        
        # Rodapé
        pagina.setFillColor(cinza_escuro)
        pagina.rect(0, 0, width, 1*cm, fill=1)
        pagina.setFillColor(colors.white)
        pagina.setFont("Helvetica", 8)
        pagina.drawString(1*cm, 0.4*cm, f"Página {num_pagina} de {total_paginas}")
        pagina.drawRightString(width - 1*cm, 0.4*cm, "Sistema de Check-ins")
    
    # Função para criar nova página
    def nova_pagina(num_pagina, total_paginas):
        p.showPage()
        adicionar_cabecalho_rodape(p, num_pagina, total_paginas)
        return height - 3*cm  # Retornar posição Y após o cabeçalho
    
    # Calcular número total de páginas (estimativa)
    # Vamos estimar 15 itens por página
    total_paginas = 1 + (len(checkins) // 15)
    
    # Agrupando check-ins por evento e oficina
    agrupados = {}
    for c in checkins:
        chave = f"EVENTO: {c.evento.nome}" if c.evento else f"OFICINA: {c.oficina.titulo if c.oficina else 'Sem título'}"
        if chave not in agrupados:
            agrupados[chave] = []
        agrupados[chave].append(c)
    
    # Iniciar primeira página
    pagina_atual = 1
    adicionar_cabecalho_rodape(p, pagina_atual, total_paginas)
    y = height - 3*cm  # Posição inicial após o cabeçalho
    
    for secao, lista in agrupados.items():
        # Verificar se tem espaço na página
        if y < 8*cm:
            y = nova_pagina(pagina_atual, total_paginas)
            pagina_atual += 1
        
        # Desenhar cabeçalho da seção
        p.setFont("Helvetica-Bold", 12)
        p.setFillColor(azul_principal)
        p.drawString(1*cm, y, secao)
        y -= 0.8*cm
        
        # Desenhar cabeçalho da tabela
        p.setFillColor(azul_principal)
        p.rect(1*cm, y - 0.7*cm, width - 2*cm, 0.7*cm, fill=1)
        
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(1.2*cm, y - 0.4*cm, "Participante")
        p.drawString(7*cm, y - 0.4*cm, "Palavra-chave")
        p.drawString(12*cm, y - 0.4*cm, "Turno")
        p.drawString(16*cm, y - 0.4*cm, "Data/Hora")
        
        y -= 0.7*cm
        
        # Listar check-ins desta seção
        linha_alternada = True
        for c in lista:
            # Verificar se tem espaço na página
            if y < 2*cm:
                y = nova_pagina(pagina_atual, total_paginas)
                pagina_atual += 1
                
                # Redesenhar cabeçalho da tabela
                p.setFillColor(azul_principal)
                p.rect(1*cm, y - 0.7*cm, width - 2*cm, 0.7*cm, fill=1)
                
                p.setFillColor(colors.white)
                p.setFont("Helvetica-Bold", 10)
                p.drawString(1.2*cm, y - 0.4*cm, "Participante")
                p.drawString(7*cm, y - 0.4*cm, "Palavra-chave")
                p.drawString(12*cm, y - 0.4*cm, "Turno")
                p.drawString(16*cm, y - 0.4*cm, "Data/Hora")
                
                y -= 0.7*cm
            
            # Alternar cores de fundo para linhas
            if linha_alternada:
                p.setFillColor(cinza_claro)
                p.rect(1*cm, y - 0.5*cm, width - 2*cm, 0.5*cm, fill=1)
            linha_alternada = not linha_alternada
            
            # Desenhar dados
            p.setFillColor(cinza_escuro)
            p.setFont("Helvetica", 9)
            p.drawString(1.2*cm, y - 0.3*cm, c.usuario.nome[:28])
            p.drawString(7*cm, y - 0.3*cm, c.palavra_chave[:20])
            p.drawString(12*cm, y - 0.3*cm, determinar_turno(c.data_hora))
            p.drawString(16*cm, y - 0.3*cm, c.data_hora.strftime('%d/%m/%Y %H:%M'))
            
            # Descer para próxima linha
            y -= 0.5*cm
        
        # Espaço entre seções
        y -= 1*cm
    
    # Finalizar PDF
    p.save()
    buffer.seek(0)
    
    nome_arquivo = f"checkins_{evento_id or 'todos'}_{tipo or 'todos'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=nome_arquivo, mimetype='application/pdf')



@login_required
def exportar_checkins_evento_pdf(evento_id):
    import os
    from io import BytesIO
    from flask import send_file, flash, redirect, url_for
    from datetime import datetime
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus.flowables import Image
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.platypus.doctemplate import SimpleDocTemplate
    from reportlab.platypus.frames import Frame
    from reportlab.platypus.tableofcontents import TableOfContents

    logger.info(
        "[DEBUG] Usuário acessou exportação de check-ins do evento ID %s",
        evento_id,
    )

    if current_user.is_cliente():
            evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
            if not evento:
                flash("Evento não encontrado ou não pertence ao seu acesso.", "danger")
                logger.info("[DEBUG] Evento não pertence ao cliente logado.")
                return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    else:
        evento = Evento.query.get_or_404(evento_id)

    logger.info("[DEBUG] Evento encontrado: %s (ID: %s)", evento.nome, evento.id)

    checkins = (
        Checkin.query
        .filter_by(evento_id=evento.id)
        .filter(Checkin.palavra_chave == 'QR-EVENTO')
        .all()
    )
    logger.info("[DEBUG] Total de check-ins encontrados: %s", len(checkins))

    if not checkins:
        flash("Nenhum check-in encontrado para este evento.", "warning")
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

    # DEBUG de alguns dados dos check-ins
    for c in checkins[:5]:
        logger.info(
            "[DEBUG] Check-in: Nome=%s, Data=%s, Palavra-chave=%s",
            c.usuario.nome,
            c.data_hora,
            c.palavra_chave,
        )

    # ...continua o restante da geração do PDF normalmente

    # Cria PDF em memória
    buffer = BytesIO()
    
    # Define cores do tema do relatório
    cor_primaria = colors.HexColor("#1E88E5")  # Azul moderno
    cor_secundaria = colors.HexColor("#E0E0E0")  # Cinza claro
    cor_destaque = colors.HexColor("#FF5722")   # Laranja para destaques
    cor_texto = colors.HexColor("#333333")      # Cinza escuro para texto
    
    # Configuração do documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"Check-ins do Evento: {evento.nome}",
        author="Sistema de Eventos",
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Titulo',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=cor_primaria,
        spaceAfter=12,
        spaceBefore=12,
    ))
    
    styles.add(ParagraphStyle(
        name='Subtitulo',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=cor_primaria,
        spaceAfter=6,
    ))
    
    # Modificar o estilo Normal existente em vez de adicionar um novo
    styles['Normal'].fontName = 'Helvetica'
    styles['Normal'].fontSize = 10
    styles['Normal'].textColor = cor_texto
    styles['Normal'].spaceAfter = 6
    
    styles.add(ParagraphStyle(
        name='InfoEvento',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        textColor=cor_texto,
        spaceAfter=10,
    ))
    
    styles.add(ParagraphStyle(
        name='Rodape',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=cor_texto,
        alignment=TA_CENTER,
    ))
    
    # Lista para elementos do documento
    elementos = []
    
    # Função para cabeçalho e rodapé
    def adicionar_cabecalho_rodape(canvas, doc):
        canvas.saveState()
        largura, altura = A4
        
        # Cabeçalho
        canvas.setFillColor(cor_primaria)
        canvas.rect(0, altura - 1.5*cm, largura, 1.5*cm, fill=1)
        
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 14)
        canvas.drawString(2*cm, altura - 1*cm, "RELATÓRIO DE CHECK-INS")
        
        # Rodapé
        canvas.setFillColor(cor_secundaria)
        canvas.rect(0, 0, largura, 1*cm, fill=1)
        
        canvas.setFillColor(cor_texto)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(2*cm, 0.5*cm, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawString(largura/2, 0.5*cm, f"Página {doc.page}")
        
        # Logo ou ícone (exemplo)
        # Se tiver um logo, substituir a linha abaixo
        canvas.setFillColor(cor_destaque)
        canvas.circle(largura - 3*cm, altura - 0.75*cm, 0.5*cm, fill=1)
        
        canvas.restoreState()
    
    # Título do relatório
    elementos.append(Paragraph(f"Relatório de Check-ins", styles['Titulo']))
    
    # Informações do evento
    elementos.append(Paragraph(f"<b>Evento:</b> {evento.nome}", styles['Subtitulo']))
    
    # Adicionar mais informações do evento se disponíveis
    if hasattr(evento, 'data'):
        elementos.append(Paragraph(f"<b>Data do evento:</b> {evento.data.strftime('%d/%m/%Y')}", styles['InfoEvento']))
    if hasattr(evento, 'local'):
        elementos.append(Paragraph(f"<b>Local:</b> {evento.local}", styles['InfoEvento']))
    
    elementos.append(Paragraph(f"<b>Total de check-ins:</b> {len(checkins)}", styles['InfoEvento']))
    elementos.append(Spacer(1, 0.5*cm))
    
    # Resumo estatístico se houver dados suficientes
    if len(checkins) > 1:
        # Dados para tabela de resumo
        resumo_data = []
        
        # Exemplo: distribuição por hora (ajuste conforme necessário)
        hora_counts = {}
        for checkin in checkins:
            hora = checkin.data_hora.hour
            hora_counts[hora] = hora_counts.get(hora, 0) + 1
        
        # Mostrar distribuição por horas se relevante
        if len(hora_counts) > 1:
            elementos.append(Paragraph("Distribuição de check-ins por hora:", styles['Subtitulo']))
            
            # Criar dados para tabela de distribuição
            hora_data = [["Hora", "Quantidade", "Percentual"]]
            for hora in sorted(hora_counts.keys()):
                qtd = hora_counts[hora]
                percentual = (qtd / len(checkins)) * 100
                hora_str = f"{hora}:00 - {hora+1}:00"
                hora_data.append([hora_str, str(qtd), f"{percentual:.1f}%"])
            
            # Criar e estilizar tabela de distribuição
            tabela_horas = Table(hora_data, colWidths=[5*cm, 3*cm, 3*cm])
            tabela_horas.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), cor_primaria),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, cor_texto),
                ('BOX', (0, 0), (-1, -1), 1, cor_primaria),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, cor_secundaria.clone(alpha=0.3)]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            elementos.append(tabela_horas)
            elementos.append(Spacer(1, 0.5*cm))
    
    # Tabela principal de check-ins
    elementos.append(Paragraph("Lista de Check-ins Realizados:", styles['Subtitulo']))
    elementos.append(Spacer(1, 0.2*cm))
    
    # Dados para tabela principal
    dados_tabela = [["Nome", "CPF", "Turno", "Data/Hora", "Palavra-chave"]]
    
    # Preencher dados na tabela
    for checkin in checkins:
        usuario = checkin.usuario
        dados_tabela.append([
            usuario.nome[:40],
            usuario.cpf or "-",
            determinar_turno(checkin.data_hora),
            checkin.data_hora.strftime('%d/%m/%Y %H:%M'),
            checkin.palavra_chave or "-"
        ])
    
    # Criar e estilizar tabela
    tabela = Table(dados_tabela, colWidths=[5*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), cor_primaria),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, cor_texto),
        ('BOX', (0, 0), (-1, -1), 1, cor_primaria),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, cor_secundaria.clone(alpha=0.2)]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    elementos.append(tabela)
    
    # Adicionar informações finais ou observações
    elementos.append(Spacer(1, 1*cm))
    elementos.append(Paragraph("* Este relatório é gerado automaticamente pelo sistema de eventos.", styles['Rodape']))
    
    # Construir documento com cabeçalho e rodapé personalizados
    doc.build(elementos, onFirstPage=adicionar_cabecalho_rodape, onLaterPages=adicionar_cabecalho_rodape)
    
    buffer.seek(0)

    filename = f"checkins_evento_{evento.id}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


@login_required
def gerar_evento_qrcode_pdf(evento_id):
    """
    Gera um PDF contendo o QR Code do evento para credenciamento.
    O PDF terá informações do evento e do participante, além do código QR.
    """

    import os
    import uuid
    from datetime import datetime
    from flask import send_file, flash, redirect, url_for
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    import qrcode

    # 1) Verifica se há configuração do cliente e se está habilitado o QR Code de evento
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=current_user.cliente_id).first()
    if not config_cliente or not config_cliente.habilitar_qrcode_evento_credenciamento:
        flash("A geração de QR Code para credenciamento de evento está desabilitada para este cliente.", "danger")
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    # 2) Localiza o evento
    evento = Evento.query.get_or_404(evento_id)

    # 3) Verifica se o participante está inscrito nesse evento, senão cria a inscrição automaticamente
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, evento_id=evento_id).first()
    if not inscricao:
        inscricao = Inscricao(
            usuario_id=current_user.id,
            cliente_id=current_user.cliente_id,
            evento_id=evento_id
        )
        db.session.add(inscricao)
        db.session.commit()

    # 4) Caso não tenha token gerado, gera agora
    if not inscricao.qr_code_token:
        novo_token = str(uuid.uuid4())
        inscricao.qr_code_token = novo_token
        db.session.commit()

    token = inscricao.qr_code_token

    # 5) Gera a imagem do QR Code
    output_dir = os.path.join("static", "tmp")
    os.makedirs(output_dir, exist_ok=True)
    qr_filename = f"qr_evento_{evento_id}_user_{current_user.id}.png"
    qr_path = os.path.join(output_dir, qr_filename)

    # Criando QR code com estilo
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)

    # Criando QR code colorido
    qr_img = qr.make_image(fill_color="#0066CC", back_color="white")
    qr_img.save(qr_path)

    # 6) Cria um PDF com ReportLab
    pdf_filename = f"evento_{evento_id}_qrcode_{current_user.id}.pdf"
    pdf_output_dir = os.path.join("static", "comprovantes")
    os.makedirs(pdf_output_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_output_dir, pdf_filename)

    # Registro de fontes personalizadas (se disponíveis)
    # Descomente as linhas abaixo se tiver arquivos de fontes
    # pdfmetrics.registerFont(TTFont('Montserrat', 'static/fonts/Montserrat-Regular.ttf'))
    # pdfmetrics.registerFont(TTFont('MontserratBold', 'static/fonts/Montserrat-Bold.ttf'))

    # Cores e estilos
    cor_primaria = colors.HexColor("#0066CC")  # Azul
    cor_secundaria = colors.HexColor("#333333")  # Cinza escuro
    cor_destaque = colors.HexColor("#FF9900")  # Laranja

    # Configurações do PDF
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    c.setTitle("Comprovante de Inscrição - " + evento.nome)

    # Fundo do cabeçalho
    c.setFillColor(cor_primaria)
    c.rect(0, height-4*cm, width, 4*cm, fill=True, stroke=False)

    # Título no cabeçalho
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width/2, height-2.5*cm, "COMPROVANTE DE INSCRIÇÃO")

    # Logo da organização (se disponível)
    # c.drawImage("static/img/logo.png", 1*cm, height-3*cm, width=2*cm, height=2*cm)

    # Data e hora de geração do comprovante
    import datetime
    data_geracao = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    c.setFont("Helvetica", 9)
    c.drawRightString(width-1*cm, height-3.5*cm, f"Gerado em: {data_geracao}")

    # Caixa principal de conteúdo
    c.setFillColor(colors.white)
    c.roundRect(1*cm, 5*cm, width-2*cm, height-10*cm, 10, fill=True, stroke=False)

    # Sombra sutil para a caixa
    c.setFillColor(colors.HexColor("#EEEEEE"))
    c.roundRect(1.1*cm, 4.9*cm, width-2*cm, height-10*cm, 10, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.roundRect(1*cm, 5*cm, width-2*cm, height-10*cm, 10, fill=True, stroke=False)

    # Informações do evento
    c.setFillColor(cor_secundaria)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2*cm, height-5.5*cm, evento.nome)

    # Linha decorativa
    c.setStrokeColor(cor_destaque)
    c.setLineWidth(3)
    c.line(2*cm, height-5.8*cm, width-2*cm, height-5.8*cm)

    # Informações detalhadas
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(cor_primaria)
    c.drawString(2*cm, height-7*cm, "DETALHES DO EVENTO:")

    c.setFillColor(cor_secundaria)
    c.setFont("Helvetica", 12)
    data_evento = evento.data_inicio.strftime("%d/%m/%Y") if evento.data_inicio else "Data indefinida"
    hora_evento = evento.hora_inicio.strftime("%H:%M") if hasattr(evento, 'hora_inicio') and evento.hora_inicio else "Horário não especificado"
    localizacao = evento.localizacao or "Local não especificado"

    y_position = height-8*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y_position, "Data:")
    c.setFont("Helvetica", 10)
    c.drawString(4*cm, y_position, data_evento)

    y_position -= 0.7*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y_position, "Horário:")
    c.setFont("Helvetica", 10)
    c.drawString(4*cm, y_position, hora_evento)

    y_position -= 0.7*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y_position, "Local:")
    c.setFont("Helvetica", 10)
    # Gerencia texto de localização longo para não sobrepor o QR code
    # Calcula a largura máxima disponível para o texto (evitando a área do QR code)
    texto_max_largura = width - 15*cm  # Deixa margem para o QR code à direita

    # Importa ferramentas para texto multilinha
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle

    # Define o estilo do parágrafo
    style = ParagraphStyle(
        name='Normal',
        fontName='Helvetica',
        fontSize=10,
        leading=12  # Espaçamento entre linhas
    )

    # Cria o parágrafo com o texto da localização
    p = Paragraph(localizacao, style)

    # Organiza o parágrafo dentro do espaço disponível
    text_width, text_height = p.wrapOn(c, texto_max_largura, 4*cm)

    # Desenha o parágrafo
    p.drawOn(c, 4*cm, y_position - text_height + 10)

    # Ajusta a posição vertical baseada na altura do texto
    y_position -= (text_height + 0.3*cm)

    # Informações do participante
    y_position -= 0.7*cm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(cor_primaria)
    c.drawString(2*cm, y_position, "DADOS DO PARTICIPANTE:")
    y_position -= 0.7*cm

    c.setFillColor(cor_secundaria)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y_position, "Nome:")
    c.setFont("Helvetica", 10)
    c.drawString(4*cm, y_position, current_user.nome)

    # Adicionar e-mail se disponível
    if hasattr(current_user, 'email'):
        y_position -= 0.7*cm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2*cm, y_position, "E-mail:")
        c.setFont("Helvetica", 10)
        c.drawString(4*cm, y_position, current_user.email)

    # Código de inscrição
    y_position -= 0.7*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y_position, "Código:")
    c.setFont("Helvetica", 10)
    codigo_inscricao = token[:8].upper()  # Primeiros 8 caracteres do token
    c.drawString(4*cm, y_position, codigo_inscricao)

    # QR Code com título
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(cor_primaria)
    c.drawString(width-7*cm, height-7*cm, "QR CODE DE ACESSO")

    # Borda decorativa ao redor do QR Code
    c.setStrokeColor(cor_destaque)
    c.setLineWidth(2)
    c.roundRect(width-7*cm, height-13*cm, 5*cm, 5*cm, 5, fill=False, stroke=True)

    # Inserir o QR Code
    c.drawImage(qr_path, width-6.5*cm, height-12.5*cm, width=4*cm, height=4*cm)

    # Instruções
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(cor_secundaria)
    c.drawCentredString(width-4.5*cm, height-13.5*cm, "Apresente este QR Code na entrada do evento")

    # Rodapé
    c.setFillColor(cor_primaria)
    c.rect(0, 0, width, 2*cm, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, 1*cm, "Este é um comprovante oficial de inscrição. Em caso de dúvidas, entre em contato conosco.")

    # Número da inscrição
    numero_inscricao = f"#{current_user.id:06d}"
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width-3*cm, 1*cm, numero_inscricao)

    # Finaliza o PDF
    c.showPage()
    c.save()

    # 7) Retorna o PDF para download
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)


def gerar_pdf_comprovante_agendamento(agendamento, horario, evento, salas, alunos, caminho_pdf):
    """
    Gera um PDF com o comprovante de agendamento para o professor.
    
    Args:
        agendamento: Objeto AgendamentoVisita
        horario: Objeto HorarioVisitacao
        evento: Objeto Evento
        salas: Lista de objetos SalaVisitacao
        alunos: Lista de objetos AlunoVisitante
        caminho_pdf: Caminho onde o PDF será salvo
    """
    
    # 1) Obter agendamentos do professor ou do mesmo cliente para o relatório
    from models import AgendamentoVisita
    from sqlalchemy import or_

    agendamentos = AgendamentoVisita.query.filter(
        or_(
            AgendamentoVisita.professor_id == agendamento.professor_id,
            AgendamentoVisita.cliente_id == agendamento.cliente_id,
        )
    ).all()
    
    # 2) Cria objeto PDF
    pdf = FPDF()
    
    # SOLUÇÃO ROBUSTA: Usar sempre Arial para evitar problemas de fontes
    logger.info("Usando Arial como fonte padrão para garantir compatibilidade total.")
    
    def set_font_safe(style='', size=12):
        """Define fonte Arial com fallback robusto"""
        try:
            pdf.set_font('Arial', style, size)
        except Exception as e:
            logger.warning(f"Erro ao definir fonte Arial: {e}. Tentando fonte padrão.")
            try:
                pdf.set_font('Helvetica', style, size)
            except Exception:
                # Último recurso - fonte básica
                pdf.set_font('Times', '', size)
    
    pdf.add_page()

    # 3) -------------------------------
    #    SEÇÃO: Relatório de Agendamentos
    # 3.1) Título
    set_font_safe('B', 16)
    pdf.cell(190, 10, f'Relatório de Agendamentos - {evento.nome}', 0, 1, 'C')
    
    # 3.2) Cabeçalho do evento
    set_font_safe('B', 12)
    pdf.cell(190, 10, f'Evento: {evento.nome}', 0, 1)
    
    set_font_safe('', 12)
    if evento.data_inicio and evento.data_fim:
        pdf.cell(
            190, 10,
            f'Período: {evento.data_inicio.strftime("%d/%m/%Y")} a {evento.data_fim.strftime("%d/%m/%Y")}',
            0, 1
        )
    else:
        pdf.cell(190, 10, 'Período: não informado', 0, 1)

    pdf.cell(190, 10, f'Local: {evento.localizacao or "Não informado"}', 0, 1)

    # 3.3) Total de agendamentos
    set_font_safe('B', 12)
    pdf.cell(190, 10, f'Total de agendamentos: {len(agendamentos)}', 0, 1)
    
    # 3.4) Resumo por status
    status_count = {'confirmado': 0, 'cancelado': 0, 'realizado': 0}
    alunos_esperados = 0
    alunos_presentes = 0
    
    for ag in agendamentos:
        status = ag.status
        status_count[status] = status_count.get(status, 0) + 1
        
        # Contar alunos
        alunos_esperados += ag.quantidade_alunos
        if ag.status == 'realizado':
            presentes = sum(1 for aluno in ag.alunos if aluno.presente)
            alunos_presentes += presentes
    
    pdf.cell(190, 10, f'Confirmados: {status_count["confirmado"]}', 0, 1)
    pdf.cell(190, 10, f'Cancelados: {status_count["cancelado"]}', 0, 1)
    pdf.cell(190, 10, f'Realizados: {status_count["realizado"]}', 0, 1)
    pdf.cell(190, 10, f'Total de alunos esperados: {alunos_esperados}', 0, 1)
    
    if alunos_presentes > 0:
        presenca = (alunos_presentes / alunos_esperados) * 100 if alunos_esperados > 0 else 0
        pdf.cell(
            190, 10,
            f'Total de alunos presentes: {alunos_presentes} ({presenca:.1f}%)',
            0, 1
        )
    
    # 3.5) Listagem de agendamentos
    pdf.ln(10)
    set_font_safe('B', 14)
    pdf.cell(190, 10, 'Listagem de Agendamentos', 0, 1, 'C')
    
    # Cabeçalho da tabela
    set_font_safe('B', 10)
    pdf.cell(20, 10, 'ID', 1, 0, 'C')
    pdf.cell(30, 10, 'Data', 1, 0, 'C')
    pdf.cell(30, 10, 'Horário', 1, 0, 'C')
    pdf.cell(50, 10, 'Escola', 1, 0, 'C')
    pdf.cell(30, 10, 'Alunos', 1, 0, 'C')
    pdf.cell(30, 10, 'Status', 1, 1, 'C')
    
    set_font_safe('', 9)
    for ag in agendamentos:
        h = ag.horario  # HorarioVisitacao
        escola_nome = ag.escola_nome
        if len(escola_nome) > 20:
            escola_nome = escola_nome[:17] + '...'
        
        pdf.cell(20, 10, str(ag.id), 1, 0, 'C')
        if h and h.data:
            pdf.cell(30, 10, h.data.strftime('%d/%m/%Y'), 1, 0, 'C')
        else:
            pdf.cell(30, 10, '--/--/----', 1, 0, 'C')
        
        if h and h.horario_inicio and h.horario_fim:
            pdf.cell(
                30, 10,
                f"{h.horario_inicio.strftime('%H:%M')} - {h.horario_fim.strftime('%H:%M')}",
                1, 0, 'C'
            )
        else:
            pdf.cell(30, 10, '---', 1, 0, 'C')
        
        pdf.cell(50, 10, escola_nome, 1, 0, 'L')
        pdf.cell(30, 10, str(ag.quantidade_alunos), 1, 0, 'C')
        pdf.cell(30, 10, ag.status.capitalize(), 1, 1, 'C')
    
    # Rodapé do relatório
    pdf.ln(10)
    set_font_safe('I', 10)
    pdf.cell(
        190, 10,
        f'Relatório gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        0, 1, 'C'
    )

    # 4) --------------------------------
    #    SEÇÃO: Comprovante de Agendamento (para este agendamento específico)
    # Precisamos de nova página para não escrever em cima do relatório
    pdf.add_page()

    set_font_safe('B', 16)
    pdf.cell(190, 10, 'Comprovante de Agendamento', 0, 1, 'C')

    # Informações do evento
    set_font_safe('B', 12)
    pdf.cell(190, 10, f'Evento: {evento.nome}', 0, 1)
    
    # Informações do agendamento
    set_font_safe('', 12)
    pdf.cell(190, 10, f'Cód. do Agendamento: #{agendamento.id}', 0, 1)

    if horario and horario.data:
        pdf.cell(190, 10, f'Data: {horario.data.strftime("%d/%m/%Y")}', 0, 1)
    else:
        pdf.cell(190, 10, 'Data: não informada', 0, 1)

    if horario and horario.horario_inicio and horario.horario_fim:
        pdf.cell(
            190, 10,
            f'Horário: {horario.horario_inicio.strftime("%H:%M")} às {horario.horario_fim.strftime("%H:%M")}',
            0, 1
        )
    else:
        pdf.cell(190, 10, 'Horário: não informado', 0, 1)
    
    if agendamento.professor:
        pdf.cell(190, 10, f'Professor: {agendamento.professor.nome}', 0, 1)
    else:
        pdf.cell(190, 10, 'Professor: --', 0, 1)

    pdf.cell(190, 10, f'Escola: {agendamento.escola_nome}', 0, 1)
    pdf.cell(190, 10, f'Turma: {agendamento.turma} - {agendamento.nivel_ensino}', 0, 1)
    pdf.cell(190, 10, f'Total de Alunos: {agendamento.quantidade_alunos}', 0, 1)
    
    if agendamento.data_agendamento:
        pdf.cell(
            190, 10,
            f'Agendado em: {agendamento.data_agendamento.strftime("%d/%m/%Y %H:%M")}',
            0, 1
        )
    else:
        pdf.cell(190, 10, 'Agendado em: --/--/---- --:--', 0, 1)
    
    # Status do agendamento
    set_font_safe('B', 12)
    pdf.cell(190, 10, f'Status: {agendamento.status.upper()}', 0, 1)
    
    # Salas selecionadas
    if salas:
        pdf.ln(5)
        set_font_safe('B', 12)
        pdf.cell(190, 10, 'Salas selecionadas:', 0, 1)
        set_font_safe('', 12)
        for sala in salas:
            pdf.cell(190, 10, f'- {sala.nome}', 0, 1)
    
    # Informações de check-in
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(190, 10, 'Informações para Check-in:', 0, 1)
    set_font_safe('', 12)
    if agendamento.checkin_realizado and agendamento.data_checkin:
        pdf.cell(
            190, 10,
            f'Check-in realizado em: {agendamento.data_checkin.strftime("%d/%m/%Y %H:%M")}',
            0, 1
        )
    else:
        pdf.cell(
            190, 10,
            'Apresente este comprovante no dia da visita para realizar o check-in.',
            0, 1
        )
    
    # 5) QR Code para check-in
    from flask import url_for
    
    # Gerar URL completa para o QR Code
    qr_url = url_for(
        'agendamento_routes.checkin_qr_agendamento',
        token=agendamento.qr_code_token,
        _external=True
    )
    
    qr = qrcode.QRCode(
        version=1, 
        box_size=12, 
        border=3,
        error_correction=qrcode.constants.ERROR_CORRECT_M
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Salvar imagem QR em buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Adicionar QR Code
    pdf.ln(10)
    pdf.cell(190, 10, 'QR Code para Check-in:', 0, 1, 'C')
    # FPDF não aceita BytesIO diretamente como caminho
    # Precisamos salvar em arquivo temporário OU usar a abordagem "tempfile"
    # Abaixo, exemplificamos salvando em um arquivo temporário
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
        temp_img.write(buffer.getvalue())
        temp_img_path = temp_img.name

    pdf.image(temp_img_path, x=75, y=pdf.get_y(), w=60)
    
    # Rodapé do comprovante
    pdf.ln(65)
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(
        190, 10,
        'Este documento é seu comprovante oficial de agendamento.',
        0, 1, 'C'
    )
    pdf.cell(
        190, 10,
        f'Emitido em {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        0, 1, 'C'
    )
    
    # 6) Finalmente, salvar o PDF (apenas uma vez!)
    pdf.output(caminho_pdf)


def gerar_pdf_relatorio_agendamentos(evento, agendamentos, caminho_pdf):
    """Gera um PDF completo de agendamentos com todas as informações detalhadas."""

    pdf = FPDF()
    
    # SOLUÇÃO ROBUSTA: Usar sempre Arial para evitar problemas de fontes
    logger.info("Usando Arial como fonte padrão para garantir compatibilidade total.")
    
    def set_font_safe(style='', size=12):
        """Define fonte Arial com fallback robusto"""
        try:
            pdf.set_font('Arial', style, size)
        except Exception as e:
            logger.warning(f"Erro ao definir fonte Arial: {e}. Tentando fonte padrão.")
            try:
                pdf.set_font('Helvetica', style, size)
            except Exception:
                # Último recurso - fonte básica
                pdf.set_font('Times', '', size)
    
    pdf.add_page()

    # Título
    set_font_safe('B', 16)
    pdf.cell(190, 10, f'Relatório Completo de Agendamentos - {evento.nome}', 0, 1, 'C')

    # Informações do evento
    set_font_safe('', 12)
    pdf.cell(190, 10, f'Local: {evento.local}', 0, 1)
    periodo = (
        f'Período: {evento.data_inicio.strftime("%d/%m/%Y")} '
        f'a {evento.data_fim.strftime("%d/%m/%Y")}'
    )
    pdf.cell(190, 10, periodo, 0, 1)

    # Data e hora de geração
    set_font_safe('I', 10)
    pdf.cell(
        190,
        10,
        f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        0,
        1,
        'R',
    )

    # Estatísticas Gerais
    pdf.ln(5)
    set_font_safe('B', 14)
    pdf.cell(190, 10, 'Estatísticas Gerais', 0, 1)

    confirmados = sum(1 for a in agendamentos if a.status == 'confirmado')
    realizados = sum(1 for a in agendamentos if a.status == 'realizado')
    cancelados = sum(1 for a in agendamentos if a.status == 'cancelado')
    pendentes = sum(1 for a in agendamentos if a.status == 'pendente')
    checkins = sum(1 for a in agendamentos if a.checkin_realizado)

    total_agendamentos = confirmados + realizados + cancelados + pendentes

    total_alunos = sum(
        a.quantidade_alunos
        for a in agendamentos
        if a.status in ['confirmado', 'realizado', 'pendente']
    )
    
    # Calcular estatísticas de PCD
    total_alunos_pcd = 0
    tipos_pcd = {}
    materiais_apoio_utilizados = set()
    
    for agendamento in agendamentos:
        for aluno in agendamento.alunos:
            if hasattr(aluno, 'necessidade_especial') and aluno.necessidade_especial:
                total_alunos_pcd += 1
                tipo_display = aluno.necessidade_especial.get_tipo_display()
                tipos_pcd[tipo_display] = tipos_pcd.get(tipo_display, 0) + 1
            
            # Materiais de apoio
            if hasattr(aluno, 'materiais_apoio'):
                for material in aluno.materiais_apoio:
                    materiais_apoio_utilizados.add(material.nome)
    
    presentes = 0
    presentes_pcd = 0
    for a in agendamentos:
        if a.status == 'realizado':
            for aluno in a.alunos:
                if aluno.presente:
                    presentes += 1
                    if hasattr(aluno, 'necessidade_especial') and aluno.necessidade_especial:
                        presentes_pcd += 1

    pdf.set_font('Arial', '', 12)
    pdf.cell(95, 10, f'Total de Agendamentos: {total_agendamentos}', 0, 0)
    pdf.cell(95, 10, f'Total de Alunos: {total_alunos}', 0, 1)

    pdf.cell(95, 10, f'Confirmados: {confirmados}', 0, 0)
    pdf.cell(95, 10, f'Realizados: {realizados}', 0, 1)

    pdf.cell(95, 10, f'Cancelados: {cancelados}', 0, 0)
    pdf.cell(95, 10, f'Pendentes: {pendentes}', 0, 1)

    pdf.cell(95, 10, f'Check-ins: {checkins}', 0, 0)
    pdf.cell(95, 10, f'Alunos Presentes: {presentes}', 0, 1)
    
    pdf.cell(95, 10, f'Alunos PCD: {total_alunos_pcd}', 0, 0)
    pdf.cell(95, 10, f'Alunos PCD Presentes: {presentes_pcd}', 0, 1)

    # Estatísticas de PCD
    if tipos_pcd:
        pdf.ln(5)
        set_font_safe('B', 12)
        pdf.cell(190, 10, 'Distribuição por Tipo de Necessidade Especial:', 0, 1)
        set_font_safe('', 10)
        for tipo, quantidade in tipos_pcd.items():
            pdf.cell(190, 8, f'• {tipo}: {quantidade} aluno(s)', 0, 1)
    
    # Materiais de apoio utilizados
    if materiais_apoio_utilizados:
        pdf.ln(3)
        set_font_safe('B', 12)
        pdf.cell(190, 10, 'Materiais de Apoio Utilizados:', 0, 1)
        set_font_safe('', 10)
        for material in sorted(materiais_apoio_utilizados):
            pdf.cell(190, 8, f'• {material}', 0, 1)

    # Detalhes dos Agendamentos
    pdf.ln(10)
    set_font_safe('B', 14)
    pdf.cell(190, 10, 'Detalhes dos Agendamentos', 0, 1)

    for i, agendamento in enumerate(agendamentos, 1):
        # Verificar se precisa de nova página
        if pdf.get_y() > 250:
            pdf.add_page()
        
        horario = agendamento.horario
        
        # Cabeçalho do agendamento
        pdf.ln(5)
        set_font_safe('B', 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(190, 8, f'Agendamento #{agendamento.id} - {agendamento.escola_nome}', 1, 1, 'L', True)
        
        # Informações básicas
        set_font_safe('', 10)
        pdf.cell(95, 6, f'Data: {horario.data.strftime("%d/%m/%Y")}', 1, 0)
        pdf.cell(95, 6, f'Horário: {horario.horario_inicio.strftime("%H:%M")} às {horario.horario_fim.strftime("%H:%M")}', 1, 1)
        
        professor_nome = agendamento.professor.nome if agendamento.professor else 'Não informado'
        pdf.cell(95, 6, f'Professor: {professor_nome}', 1, 0)
        pdf.cell(95, 6, f'Status: {agendamento.status.capitalize()}', 1, 1)
        
        pdf.cell(95, 6, f'Turma: {agendamento.turma}', 1, 0)
        pdf.cell(95, 6, f'Nível: {agendamento.nivel_ensino}', 1, 1)
        
        pdf.cell(95, 6, f'Total de Alunos: {agendamento.quantidade_alunos}', 1, 0)
        
        # Contar alunos PCD neste agendamento
        alunos_pcd_agendamento = sum(
            1 for aluno in agendamento.alunos 
            if hasattr(aluno, 'necessidade_especial') and aluno.necessidade_especial
        )
        pdf.cell(95, 6, f'Alunos PCD: {alunos_pcd_agendamento}', 1, 1)
        
        # Check-in
        if agendamento.checkin_realizado and agendamento.data_checkin:
            pdf.cell(190, 6, f'Check-in realizado em: {agendamento.data_checkin.strftime("%d/%m/%Y %H:%M")}', 1, 1)
        else:
            pdf.cell(190, 6, 'Check-in: Não realizado', 1, 1)
        
        # Observações
        if agendamento.observacoes:
            pdf.cell(190, 6, f'Observações: {agendamento.observacoes[:80]}...', 1, 1)
        
        # Lista de alunos com detalhes
        if agendamento.alunos:
            pdf.ln(2)
            set_font_safe('B', 10)
            pdf.cell(190, 6, 'Lista de Alunos:', 0, 1)
            
            # Cabeçalho da tabela de alunos
            set_font_safe('B', 8)
            pdf.cell(50, 6, 'Nome', 1, 0, 'C')
            pdf.cell(20, 6, 'Presente', 1, 0, 'C')
            pdf.cell(40, 6, 'Tipo PCD', 1, 0, 'C')
            pdf.cell(40, 6, 'Descrição', 1, 0, 'C')
            pdf.cell(40, 6, 'Materiais de Apoio', 1, 1, 'C')
            
            set_font_safe('', 7)
            for aluno in agendamento.alunos:
                # Verificar se precisa de nova página
                if pdf.get_y() > 270:
                    pdf.add_page()
                    # Repetir cabeçalho
                    set_font_safe('B', 8)
                    pdf.cell(50, 6, 'Nome', 1, 0, 'C')
                    pdf.cell(20, 6, 'Presente', 1, 0, 'C')
                    pdf.cell(40, 6, 'Tipo PCD', 1, 0, 'C')
                    pdf.cell(40, 6, 'Descrição', 1, 0, 'C')
                    pdf.cell(40, 6, 'Materiais de Apoio', 1, 1, 'C')
                    set_font_safe('', 7)
                
                nome = aluno.nome[:25] + '...' if len(aluno.nome) > 25 else aluno.nome
                presente = 'Sim' if aluno.presente else 'Não'
                
                tipo_pcd = ''
                descricao_pcd = ''
                materiais = ''
                
                if hasattr(aluno, 'necessidade_especial') and aluno.necessidade_especial:
                    tipo_pcd = aluno.necessidade_especial.get_tipo_display()[:20]
                    descricao_pcd = aluno.necessidade_especial.descricao[:25] + '...' if len(aluno.necessidade_especial.descricao) > 25 else aluno.necessidade_especial.descricao
                
                if hasattr(aluno, 'materiais_apoio') and aluno.materiais_apoio:
                    materiais_lista = [m.nome for m in aluno.materiais_apoio]
                    materiais = ', '.join(materiais_lista)[:25] + '...' if len(', '.join(materiais_lista)) > 25 else ', '.join(materiais_lista)
                
                pdf.cell(50, 6, nome, 1, 0, 'L')
                pdf.cell(20, 6, presente, 1, 0, 'C')
                pdf.cell(40, 6, tipo_pcd, 1, 0, 'L')
                pdf.cell(40, 6, descricao_pcd, 1, 0, 'L')
                pdf.cell(40, 6, materiais, 1, 1, 'L')

    # Rodapé
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(
        190,
        10,
        'Este relatório completo é gerado automaticamente pelo sistema de agendamentos.',
        0,
        1,
        'C',
    )

    # Salvar o PDF
    pdf.output(caminho_pdf)
    
# Funções para manipulação de QR Code e checkin
import qrcode
from PIL import Image
import io
import os
from flask import send_file

def gerar_qrcode_url(token, tamanho=200):
    """
    Gera uma imagem QR Code para um token de agendamento
    
    Args:
        token: Token único do agendamento
        tamanho: Tamanho da imagem em pixels
        
    Returns:
        BytesIO: Buffer contendo a imagem do QR Code em formato PNG
    """
    from flask import url_for
    
    # Preparar a URL completa para o QR Code
    url = url_for(
        'agendamento_routes.checkin_qr_agendamento',
        token=token,
        _external=True
    )
    
    # Gerar QR Code com configurações otimizadas
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # Melhor correção de erro
        box_size=12,  # Tamanho maior para melhor legibilidade
        border=3,     # Borda menor para economizar espaço
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Criar imagem com alta qualidade
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Redimensionar se necessário
    if tamanho != 200:
        img = img.resize((tamanho, tamanho), Image.LANCZOS)
    
    # Salvar em um buffer em memória
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    
    return buffer



def gerar_qrcode_token(token):
    """
    Endpoint para gerar e retornar uma imagem QR Code para um token
    """
    buffer = gerar_qrcode_url(token)
    return send_file(buffer, mimetype='image/png')


def gerar_programacao_evento_pdf(evento_id):
    """Gera um PDF profissional e organizado da programação do evento"""
    from models import Evento, Oficina
    from extensions import db
    from flask import current_app, send_file
    import os
    from datetime import datetime
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Frame, PageTemplate, BaseDocTemplate
    )
    from reportlab.platypus.tableofcontents import TableOfContents

    # 1. Data Retrieval and Preparation
    evento = Evento.query.get_or_404(evento_id)

    oficinas = (
        Oficina.query
        .filter_by(evento_id=evento_id)
        .options(db.joinedload(Oficina.dias), db.joinedload(Oficina.ministrante_obj))
        .all()
    )

    # Agrupar oficinas por data
    grouped_oficinas = {}
    for oficina in oficinas:
        for dia in oficina.dias:
            data_str = dia.data.strftime('%d/%m/%Y')
            if data_str not in grouped_oficinas:
                grouped_oficinas[data_str] = []
            
            # Tratar horários que podem ser string ou datetime
            def format_horario(horario):
                if not horario:
                    return ''
                if isinstance(horario, str):
                    return horario
                return horario.strftime('%H:%M')
            
            grouped_oficinas[data_str].append({
                'titulo': oficina.titulo,
                'ministrante': oficina.ministrante_obj.nome if oficina.ministrante_obj else 'A definir',
                'inicio': format_horario(dia.horario_inicio),
                'fim': format_horario(dia.horario_fim),
                'descricao': getattr(oficina, 'descricao', '') or '',
                'local': getattr(oficina, 'local', '') or ''
            })

    # Ordenar datas
    sorted_dates = sorted(
        grouped_oficinas.keys(), 
        key=lambda d: datetime.strptime(d, '%d/%m/%Y')
    )

    # 2. PDF File Setup
    pdf_dir = os.path.join(current_app.static_folder, 'programacoes', str(evento_id))
    os.makedirs(pdf_dir, exist_ok=True)
    filename = f"programacao_evento_{evento_id}.pdf"
    pdf_path = os.path.join(pdf_dir, filename)

    # 3. Create Document with Custom Styles
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm
    )

    # 4. Define Custom Styles
    styles = getSampleStyleSheet()
    
    # Cores do tema
    primary_color = HexColor('#2C3E50')      # Azul escuro
    secondary_color = HexColor('#3498DB')     # Azul claro
    accent_color = HexColor('#E74C3C')        # Vermelho
    text_color = HexColor('#34495E')          # Cinza escuro
    light_gray = HexColor('#ECF0F1')          # Cinza claro
    
    # Estilos customizados
    styles.add(ParagraphStyle(
        name='EventTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=primary_color,
        alignment=TA_CENTER,
        spaceAfter=8*mm,
        spaceBefore=5*mm,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='EventSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=secondary_color,
        alignment=TA_CENTER,
        spaceAfter=12*mm,
        fontName='Helvetica-Oblique'
    ))
    
    styles.add(ParagraphStyle(
        name='EventDescription',
        parent=styles['Normal'],
        fontSize=11,
        textColor=text_color,
        alignment=TA_JUSTIFY,
        spaceAfter=15*mm,
        leading=14
    ))
    
    styles.add(ParagraphStyle(
        name='DateHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=primary_color,
        spaceBefore=15*mm,
        spaceAfter=8*mm,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderColor=secondary_color,
        borderPadding=3*mm
    ))
    
    styles.add(ParagraphStyle(
        name='OficinaTitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=primary_color,
        fontName='Helvetica-Bold',
        spaceAfter=2*mm
    ))
    
    styles.add(ParagraphStyle(
        name='OficinaDetails',
        parent=styles['Normal'],
        fontSize=10,
        textColor=text_color,
        leftIndent=5*mm,
        spaceAfter=1*mm
    ))
    
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor('#7F8C8D'),
        alignment=TA_CENTER,
        spaceBefore=20*mm
    ))

    # 5. Build Document Content
    story = []
    
    # Cabeçalho do evento
    story.append(Paragraph(f"{evento.nome}", styles['EventTitle']))
    
    if hasattr(evento, 'data_inicio') and evento.data_inicio:
        data_evento = evento.data_inicio.strftime('%d de %B de %Y')
        story.append(Paragraph(f"Programação do Evento - {data_evento}", styles['EventSubtitle']))
    else:
        story.append(Paragraph("Programação do Evento", styles['EventSubtitle']))
    
    # Descrição do evento
    if evento.descricao:
        story.append(Paragraph(evento.descricao, styles['EventDescription']))
    
    # Linha separadora
    story.append(Spacer(1, 5*mm))
    
    # Programação por data
    for i, data in enumerate(sorted_dates):
        # Cabeçalho da data
        data_dt = datetime.strptime(data, '%d/%m/%Y')
        data_formatada = f"{dia_semana(data_dt)}, {data_dt.strftime('%d de %B de %Y')}"
        story.append(Paragraph(data_formatada, styles['DateHeader']))
        
        # Criar tabela para as oficinas do dia
        oficinas_do_dia = sorted(grouped_oficinas[data], key=lambda x: x['inicio'])
        
        if oficinas_do_dia:
            # Dados da tabela
            table_data = [['Horário', 'Oficina', 'Ministrante']]
            
            for oficina in oficinas_do_dia:
                horario = f"{oficina['inicio']} - {oficina['fim']}" if oficina['inicio'] and oficina['fim'] else "A definir"
                
                # Título da oficina
                titulo_oficina = oficina['titulo']
                if oficina['local']:
                    titulo_oficina += f"<br/><i>Local: {oficina['local']}</i>"
                
                # Descrição se houver
                if oficina['descricao']:
                    descricao_truncada = oficina['descricao'][:100] + "..." if len(oficina['descricao']) > 100 else oficina['descricao']
                    titulo_oficina += f"<br/><font size='9' color='#7F8C8D'>{descricao_truncada}</font>"
                
                table_data.append([
                    horario,
                    Paragraph(titulo_oficina, styles['Normal']),
                    oficina['ministrante']
                ])
            
            # Criar e estilizar tabela
            table = Table(table_data, colWidths=[3.5*cm, 9*cm, 4*cm])
            table.setStyle(TableStyle([
                # Cabeçalho
                ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8*mm),
                ('TOPPADDING', (0, 0), (-1, 0), 8*mm),
                
                # Corpo da tabela
                ('BACKGROUND', (0, 1), (-1, -1), white),
                ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Horário centralizado
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Oficina à esquerda
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Ministrante à esquerda
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, light_gray]),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#BDC3C7')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5*mm),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5*mm),
                ('TOPPADDING', (0, 1), (-1, -1), 5*mm),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8*mm),
            ]))
            
            story.append(table)
        else:
            story.append(Paragraph("Nenhuma oficina programada para este dia.", styles['OficinaDetails']))
        
        story.append(Spacer(1, 8*mm))
        
        # Quebra de página entre datas (exceto na última)
        if i < len(sorted_dates) - 1:
            story.append(PageBreak())
    
    # Rodapé
    footer_text = f"Documento gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
    if hasattr(evento, 'organizador') and evento.organizador:
        footer_text += f"<br/>Organização: {evento.organizador}"
    if hasattr(evento, 'contato') and evento.contato:
        footer_text += f"<br/>Contato: {evento.contato}"
        
    story.append(Paragraph(footer_text, styles['Footer']))

    # 6. Build PDF
    doc.build(story)

    return send_file(pdf_path, as_attachment=True, download_name=filename, mimetype='application/pdf')


import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from textwrap import wrap

def gerar_placas_oficinas_pdf(evento_id):
    """
    Gera um PDF com placas individuais, modernas e harmoniosas para cada oficina de um evento.
    O design foi aprimorado para ter um visual mais profissional, com gradientes,
    ícones vetoriais e uma hierarquia visual clara.
    """
    from models import Evento, Oficina
    from extensions import db
    from flask import current_app, send_file

    # --- Paleta de Cores Refinada ---
    COLORS = {
        'primary_dark': HexColor('#0D1B2A'),    # Azul quase preto para textos principais
        'primary_medium': HexColor('#1B263B'),  # Azul escuro para fundos de destaque
        'primary_light': HexColor('#415A77'),   # Azul acinzentado para subtextos
        'accent': HexColor('#E0E1DD'),          # Bege claro para detalhes e fundos
        'highlight': HexColor('#D90429'),       # Vermelho vibrante para destaques importantes
        'white': HexColor('#FFFFFF'),
        'light_gray': HexColor('#F8F9FA'),
        'shadow': Color(0, 0, 0, alpha=0.15)
    }

    # --- Funções de Desenho Auxiliares ---

    def draw_background(c, width, height):
        """Desenha um fundo com um gradiente vertical sutil."""
        # O gradiente vai do cinza claro (topo) para o branco (base)
        c.setFillColor(COLORS['light_gray'])
        c.rect(0, 0, width, height, fill=1, stroke=0)
        # Adiciona um retângulo decorativo na base
        c.setFillColor(COLORS['primary_medium'])
        c.rect(0, 0, width, 2*cm, fill=1, stroke=0)

    def draw_card(c, x, y, width, height):
        """Desenha o cartão principal com sombra e bordas arredondadas."""
        # Sombra sutil
        c.setFillColor(COLORS['shadow'])
        c.roundRect(x + 0.1*cm, y - 0.1*cm, width, height, radius=0.5*cm, fill=1, stroke=0)
        
        # Cartão branco
        c.setFillColor(COLORS['white'])
        c.roundRect(x, y, width, height, radius=0.5*cm, fill=1, stroke=0)

    def draw_header(c, x, y, width, height):
        """Desenha a faixa de destaque no topo do cartão."""
        c.setFillColor(COLORS['highlight'])
        c.roundRect(x, y + height - 1.5*cm, width, 1.5*cm, radius=0.5*cm, fill=1, stroke=0)

    def draw_workshop_title(c, box, title):
        """Desenha o título da oficina, centralizado e com quebra de linha automática."""
        c.setFillColor(COLORS['primary_dark'])
        
        # Tenta diferentes tamanhos de fonte para caber o título
        for size in [32, 28, 24, 20]:
            c.setFont('Helvetica-Bold', size)
            lines = wrap(title, width=int(box.width / (size * 0.02))) # Heurística para quebra
            line_height = size * 1.2
            total_height = len(lines) * line_height
            if total_height < box.height:
                break
        
        start_y = box.y + box.height - (box.height - total_height) / 2
        
        for i, line in enumerate(lines):
            text_width = c.stringWidth(line, 'Helvetica-Bold', size)
            c.drawCentredString(box.x + box.width / 2, start_y - i * line_height, line)

    def draw_info_block(c, box, icon_func, primary_text, secondary_text=""):
        """
        Desenha um bloco de informação genérico com ícone, texto primário e secundário.
        Retorna a altura total do bloco desenhado.
        """
        icon_size = 0.8 * cm
        padding = 0.5 * cm
        text_x = box.x + icon_size + padding
        text_width = box.width - icon_size - padding

        # Desenha o ícone
        icon_func(c, box.x, box.y + (box.height - icon_size) / 2, icon_size)

        # Texto Primário (ex: Nome do ministrante)
        c.setFont('Helvetica-Bold', 16)
        c.setFillColor(COLORS['primary_dark'])
        c.drawString(text_x, box.y + box.height * 0.55, primary_text)
        
        # Texto Secundário (ex: Formação)
        if secondary_text:
            c.setFont('Helvetica', 12)
            c.setFillColor(COLORS['primary_light'])
            c.drawString(text_x, box.y + box.height * 0.2, secondary_text)
        
        return box.height + 0.5*cm # Retorna altura do bloco mais um espaçamento

    # --- Funções para Desenhar Ícones Vetoriais ---

    def draw_user_icon(c, x, y, size):
        c.setFillColor(COLORS['primary_light'])
        c.setStrokeColor(COLORS['primary_light'])
        c.setLineWidth(2)
        # Cabeça
        c.circle(x + size/2, y + size*0.65, size*0.2, fill=0)
        # Corpo
        path = c.beginPath()
        path.moveTo(x + size*0.2, y + size*0.4)
        path.lineTo(x + size*0.8, y + size*0.4)
        path.arcTo(x, y, x + size, y + size*0.8, startAng=200, endAng=340)
        c.drawPath(path, fill=0)

    def draw_calendar_icon(c, x, y, size):
        c.setFillColor(COLORS['primary_light'])
        c.setStrokeColor(COLORS['primary_light'])
        c.setLineWidth(2)
        # Corpo do calendário
        c.roundRect(x, y, size, size, radius=size*0.1, fill=0)
        # Linha do topo
        c.line(x, y + size*0.7, x + size, y + size*0.7)
        # Pinos do fichário
        c.rect(x + size*0.2, y + size*0.7, size*0.1, size*0.2, fill=1, stroke=0)
        c.rect(x + size*0.7, y + size*0.7, size*0.1, size*0.2, fill=1, stroke=0)

    def draw_pin_icon(c, x, y, size):
        c.setFillColor(COLORS['primary_light'])
        c.setStrokeColor(COLORS['primary_light'])
        c.setLineWidth(2)
        path = c.beginPath()
        path.moveTo(x + size/2, y + size)
        path.arcTo(x, y + size*0.2, x + size, y + size, startAng=180, endAng=0)
        path.lineTo(x + size/2, y)
        c.drawPath(path, fill=0)
        c.circle(x + size/2, y + size*0.65, size*0.15, fill=1, stroke=0)

    # --- Classe para gerenciar caixas de layout ---
    class BoundingBox:
        def __init__(self, x, y, width, height):
            self.x = x
            self.y = y
            self.width = width
            self.height = height

    # --- Lógica Principal ---

    evento = Evento.query.get_or_404(evento_id)
    oficinas = (
        Oficina.query
        .filter_by(evento_id=evento_id)
        .options(db.joinedload(Oficina.dias), db.joinedload(Oficina.ministrante_obj))
        .all()
    )

    pdf_dir = os.path.join(current_app.static_folder, 'placas', str(evento_id))
    os.makedirs(pdf_dir, exist_ok=True)
    filename = f"placas_oficinas_{evento_id}.pdf"
    pdf_path = os.path.join(pdf_dir, filename)

    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    page_width, page_height = landscape(A4)

    for oficina in oficinas:
        draw_background(c, page_width, page_height)
        
        # Define a área do cartão principal
        card_margin = 2.5 * cm
        card_width = page_width - 2 * card_margin
        card_height = page_height - 2 * card_margin
        draw_card(c, card_margin, card_margin, card_width, card_height)
        
        # Define a área de conteúdo dentro do cartão
        content_padding = 1.5 * cm
        content_box = BoundingBox(
            card_margin + content_padding,
            card_margin,
            card_width - 2 * content_padding,
            card_height - content_padding
        )
        
        # --- Desenha o Título ---
        title_box = BoundingBox(
            content_box.x,
            content_box.y + content_box.height * 0.6,
            content_box.width,
            content_box.height * 0.4
        )
        draw_workshop_title(c, title_box, oficina.titulo)
        
        # Posição inicial para os blocos de informação
        current_y = content_box.y + content_box.height * 0.5
        
        # --- Bloco do Ministrante ---
        if oficina.ministrante_obj:
            info_box = BoundingBox(content_box.x, current_y - 1.5*cm, content_box.width, 1.5*cm)
            height_drawn = draw_info_block(
                c, info_box, draw_user_icon,
                f"Ministrante: {oficina.ministrante_obj.nome}",
                oficina.ministrante_obj.formacao
            )
            current_y -= height_drawn

        # --- Bloco da Programação ---
        if oficina.dias:
            # Helper para obter um objeto de data para ordenação, tratando strings.
            def get_date_for_sort(d):
                if hasattr(d.data, 'strftime'):
                    return d.data
                try:
                    # Tenta converter uma data em string (formato comum de BD).
                    return datetime.strptime(str(d.data), '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    # Se a conversão falhar, retorna uma data que ficará por último na ordenação.
                    return datetime.max.date()

            dias_sorted = sorted(oficina.dias, key=get_date_for_sort)
            
            for dia in dias_sorted:
                # Formata a data de forma segura
                if hasattr(dia.data, 'strftime'):
                    data_str = dia.data.strftime('%d/%m/%Y')
                else:
                    data_str = str(dia.data)

                # Formata a hora de início de forma segura
                if hasattr(dia.horario_inicio, 'strftime'):
                    inicio_str = dia.horario_inicio.strftime('%H:%M')
                else:
                    inicio_str = str(dia.horario_inicio)

                # Formata a hora de fim de forma segura
                if hasattr(dia.horario_fim, 'strftime'):
                    fim_str = dia.horario_fim.strftime('%H:%M')
                else:
                    fim_str = str(dia.horario_fim)
                
                horario_str = f"{inicio_str} - {fim_str}"

                info_box = BoundingBox(content_box.x, current_y - 1.5*cm, content_box.width, 1.5*cm)
                height_drawn = draw_info_block(c, info_box, draw_calendar_icon, data_str, horario_str)
                current_y -= height_drawn

        # --- Bloco do Local ---
        if hasattr(oficina, 'local') and oficina.local:
            info_box = BoundingBox(content_box.x, current_y - 1.5*cm, content_box.width, 1.5*cm)
            height_drawn = draw_info_block(c, info_box, draw_pin_icon, "Local", oficina.local)
            current_y -= height_drawn

        # --- Rodapé com nome do evento ---
        c.setFont('Helvetica', 10)
        c.setFillColor(COLORS['primary_light'])
        c.drawCentredString(page_width / 2, card_margin - 1*cm, evento.nome)
        
        c.showPage()
    
    c.save()
    
    return send_file(pdf_path, as_attachment=True, download_name=f"Placas_{evento.nome}.pdf", mimetype='application/pdf')


def gerar_etiquetas(cliente_id):
    """Gera um PDF de etiquetas para o cliente"""
    if current_user.tipo != 'cliente' or current_user.id != cliente_id:
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

    pdf_path = gerar_etiquetas_pdf(cliente_id)
    if not pdf_path:
        flash("Nenhum usuário encontrado para gerar etiquetas!", "warning")
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

    return send_file(pdf_path, as_attachment=True)


import requests
from reportlab.lib.units import inch
import os
import base64
import json
import google.auth
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from models import CertificadoTemplate, Oficina, Inscricao
from models.user import Usuario, Cliente
from models.event import Evento
from flask_mail import Message
from extensions import mail
import logging
from models import CertificadoTemplate


# ReportLab para PDFs
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Logger do módulo
logger = logging.getLogger(__name__)

# Escopo necessário para envio de e-mails
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
# Configuracoes de OAuth
TOKEN_FILE = "token.json"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
TOKEN_ENV_VAR = "GMAIL_TOKEN"
TOKEN_FILE_ENV_VAR = "GMAIL_TOKEN_FILE"

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise EnvironmentError(
        "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in the environment"
    )

from decimal import Decimal, ROUND_HALF_UP
from models import Configuracao

def preco_com_taxa(base):
    """
    Recebe o preço digitado pelo cliente (Decimal, str ou float)
    e devolve o valor acrescido do percentual configurado.
    """
    if not base:
        try:
            return Decimal(str(base)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        except Exception:
            return Decimal("0").quantize(Decimal("0.01"), ROUND_HALF_UP)

    base = Decimal(str(base))
    cfg  = Configuracao.query.first()
    perc = Decimal(str(cfg.taxa_percentual_inscricao or 0))
    valor = base * (1 + perc/100)
    # duas casas, arredondamento comercial
    return valor.quantize(Decimal("0.01"), ROUND_HALF_UP)


def gerar_qr_code_inscricao(qr_code_token):
    """Gera o QR Code para a inscrição com base no token único."""
    caminho_pasta = os.path.join('static', 'qrcodes_inscricoes')
    os.makedirs(caminho_pasta, exist_ok=True)
    
    nome_arquivo = f'inscricao_{qr_code_token}.png'
    caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
    
    # Se quiser testar localmente, use http://127.0.0.1:5000
    # Em produção, use seu domínio real, ex.: https://www.appfiber.com.br
    #qr_data = f"http://127.0.0.1:5000/leitor_checkin?token={qr_code_token}"
    qr_data = f"https://www.appfiber.com.br/leitor_checkin?token={qr_code_token}"

    # IMPORTANTE: a URL/URI que será codificada aponta para uma rota
    # que faz o check-in ao ser acessada, ou que o app web decodifica e chama.
    # Se estiver testando localmente:
   

    # Se quiser usar a URL definitiva de produção:
    # QR_DATA= f"https://www.appfiber.com.br/leitor_checkin?token={qr_code_token}"
    
    img_qr = qrcode.make(qr_data)
    img_qr.save(caminho_completo)

    return caminho_completo

def obter_estados():
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
    response = requests.get(url)
    
    if response.status_code == 200:
        estados = response.json()
        return sorted([(estado["sigla"], estado["nome"]) for estado in estados], key=lambda x: x[1])
    return []

def obter_cidades(estado_sigla):
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{estado_sigla}/municipios"
    response = requests.get(url)
    
    if response.status_code == 200:
        cidades = response.json()
        return sorted([cidade["nome"] for cidade in cidades])
    return []

def gerar_qr_code(oficina_id):
    caminho_pasta = os.path.join('static', 'qrcodes')
    os.makedirs(caminho_pasta, exist_ok=True)  # Garante que a pasta exista
    
    nome_arquivo = f'checkin_{oficina_id}.png'
    caminho_completo = os.path.join(caminho_pasta, nome_arquivo)

    qr = qrcode.make(f'http://127.0.0.1:5000/checkin/{oficina_id}')
    qr.save(caminho_completo)

    return os.path.join("qrcodes", nome_arquivo)


from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
import os
from datetime import datetime

def gerar_etiquetas_pdf(cliente_id, evento_id=None):
    """
    Gera um PDF com etiquetas simples em preto e branco contendo Nome, ID, QR Code e informações do evento.
    Layout otimizado para 9 etiquetas por página A4 (3x3).
    Se evento_id for fornecido, apenas gera etiquetas para os usuários inscritos nesse evento.
    """
    
    # Configurações de layout para 9 etiquetas por página A4 (3x3)
    etiqueta_largura = 65 * mm
    etiqueta_altura = 85 * mm
    margem_esquerda = 12 * mm
    margem_superior = 15 * mm
    margem_inferior = 15 * mm
    espacamento_x = 5 * mm
    espacamento_y = 5 * mm
    
    # Cores simples preto e branco
    cor_texto = colors.black
    cor_borda = colors.black
    cor_fundo = colors.white
    
    # Buscar informações do evento se o evento_id foi fornecido
    evento = None
    if evento_id:
        evento = Evento.query.get(evento_id)
        if not evento:
            return None
    
    # Nome do arquivo baseado no evento ou cliente
    if evento:
        pdf_filename = f"etiquetas_evento_{evento.id}_{evento.nome.replace(' ', '_')}.pdf"
    else:
        pdf_filename = f"etiquetas_cliente_{cliente_id}.pdf"
    
    pdf_path = os.path.join("static", "etiquetas", pdf_filename)
    os.makedirs("static/etiquetas", exist_ok=True)
    
    # Documento A4 retrato para layout 3x3
    c = canvas.Canvas(pdf_path, pagesize=A4)
    largura_pagina, altura_pagina = A4
    
    # Layout fixo 3x3 = 9 etiquetas por página
    max_colunas = 3
    max_linhas = 3
    
    # Buscar usuários com base no evento ou cliente
    usuarios = []
    if evento_id:
        # Buscar apenas usuários inscritos no evento específico
        inscricoes = Inscricao.query.filter_by(evento_id=evento_id, cliente_id=cliente_id).all()
        usuario_ids = [insc.usuario_id for insc in inscricoes]
        if usuario_ids:
            usuarios = Usuario.query.filter(Usuario.id.in_(usuario_ids)).all()
    else:
        # Buscar todos os usuários do cliente
        usuarios = Usuario.query.filter_by(cliente_id=cliente_id).all()
    
    if not usuarios:
        return None
    
    linha = 0
    coluna = 0
    
    # Cabeçalho simples preto e branco
    def desenhar_cabecalho():
        # Linha horizontal simples
        c.setStrokeColor(cor_borda)
        c.setLineWidth(1)
        c.line(margem_esquerda, altura_pagina - 12*mm, largura_pagina - margem_esquerda, altura_pagina - 12*mm)
        
        # Texto do cabeçalho
        c.setFillColor(cor_texto)
        c.setFont("Helvetica-Bold", 10)
        
        if evento:
            # Limitar o tamanho do nome do evento no cabeçalho
            nome_evento = evento.nome
            if len(nome_evento) > 35:
                nome_evento = nome_evento[:32] + "..."
            c.drawString(margem_esquerda, altura_pagina - 10*mm, f"ETIQUETAS - {nome_evento}")
        else:
            c.drawString(margem_esquerda, altura_pagina - 10*mm, f"ETIQUETAS - CLIENTE {cliente_id}")
        
        # Data gerada à direita
        data_atual = datetime.utcnow().strftime('%d/%m/%Y')
        c.drawRightString(largura_pagina - margem_esquerda, altura_pagina - 10*mm, f"{data_atual}")
    
    desenhar_cabecalho()
    
    # Contador de etiquetas geradas
    total_etiquetas = 0
    
    for usuario in usuarios:
        # Obter a inscrição específica do usuário para este evento
        if evento_id:
            inscricao = Inscricao.query.filter_by(usuario_id=usuario.id, evento_id=evento_id).first()
            if not inscricao:
                continue  # Pula para o próximo usuário se não tiver inscrição para este evento
        else:
            inscricao = Inscricao.query.filter_by(usuario_id=usuario.id).first()
        
        # Verifica se precisa mudar de coluna/linha
        if coluna >= max_colunas:
            coluna = 0
            linha += 1
        
        # Verifica se precisa de uma nova página
        if linha >= max_linhas:
            c.showPage()
            desenhar_cabecalho()
            linha = 0
            coluna = 0
        
        # Posição do canto superior esquerdo da etiqueta
        x = margem_esquerda + coluna * (etiqueta_largura + espacamento_x)
        y = altura_pagina - margem_superior - linha * (etiqueta_altura + espacamento_y)
        
        # Design simples com borda retangular
        # Fundo branco com borda preta
        c.setFillColor(cor_fundo)
        c.setStrokeColor(cor_borda)
        c.setLineWidth(1)
        c.rect(x, y - etiqueta_altura, etiqueta_largura, etiqueta_altura, fill=1, stroke=1)
        
        # Linha horizontal para separar seções
        linha_separacao_y = y - 25*mm
        c.setStrokeColor(cor_borda)
        c.setLineWidth(0.5)
        c.line(x + 3*mm, linha_separacao_y, x + etiqueta_largura - 3*mm, linha_separacao_y)
        
        # Nome do usuário centralizado
        nome = usuario.nome
        if len(nome) > 18:  # Limite para caber na etiqueta
            nome = nome[:16] + "..."
        
        c.setFillColor(cor_texto)
        c.setFont("Helvetica-Bold", 12)
        # Centralizado horizontalmente
        nome_largura = c.stringWidth(nome, "Helvetica-Bold", 12)
        nome_x = x + (etiqueta_largura - nome_largura) / 2
        nome_y = y - 12*mm
        c.drawString(nome_x, nome_y, nome)
        
        # ID do usuário centralizado
        id_str = f"ID: {usuario.id}"
        c.setFont("Helvetica", 10)
        c.setFillColor(cor_texto)
        id_largura = c.stringWidth(id_str, "Helvetica", 10)
        id_x = x + (etiqueta_largura - id_largura) / 2
        c.drawString(id_x, nome_y - 8*mm, id_str)
        
        # Adicionar informações do evento à etiqueta (abaixo da linha)
        if evento:
            # Nome do evento centralizado
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(cor_texto)
            evento_str = evento.nome
            if len(evento_str) > 20:  # Limite para o nome do evento
                evento_str = evento_str[:18] + "..."
            evento_largura = c.stringWidth(evento_str, "Helvetica-Bold", 9)
            evento_x = x + (etiqueta_largura - evento_largura) / 2
            c.drawString(evento_x, linha_separacao_y - 8*mm, evento_str)
            
            # Data do evento centralizada
            if evento.data_inicio:
                data_evento = evento.data_inicio.strftime('%d/%m/%Y')
                if evento.data_fim and evento.data_fim != evento.data_inicio:
                    data_evento += f" - {evento.data_fim.strftime('%d/%m/%Y')}"
                
                c.setFont("Helvetica", 8)
                c.setFillColor(cor_texto)
                data_largura = c.stringWidth(data_evento, "Helvetica", 8)
                data_x = x + (etiqueta_largura - data_largura) / 2
                c.drawString(data_x, linha_separacao_y - 15*mm, data_evento)
        
        # QR Code centralizado na parte inferior
        if inscricao and inscricao.qr_code_token:
            qr_size = 20 * mm  # Tamanho menor para caber melhor
            qr_code_path = gerar_qr_code_inscricao(inscricao.qr_code_token)
            
            try:
                qr_image = ImageReader(qr_code_path)
                # Centralizado horizontalmente na parte inferior
                qr_x = x + (etiqueta_largura - qr_size) / 2
                qr_y = y - etiqueta_altura + 8*mm
                
                c.drawImage(qr_image, qr_x, qr_y, qr_size, qr_size)
                
                # Token abaixo do QR Code
                token_curto = inscricao.qr_code_token[:8]
                c.setFont("Helvetica", 7)
                c.setFillColor(cor_texto)
                token_largura = c.stringWidth(token_curto, "Helvetica", 7)
                token_x = x + (etiqueta_largura - token_largura) / 2
                c.drawString(token_x, qr_y - 4*mm, token_curto)
            except Exception:
                # Fallback de texto se não for possível desenhar o QR
                c.setFont("Helvetica", 8)
                c.setFillColor(cor_texto)
                token_text = f"Token: {inscricao.qr_code_token[:10]}..."
                token_largura = c.stringWidth(token_text, "Helvetica", 8)
                token_x = x + (etiqueta_largura - token_largura) / 2
                c.drawString(token_x, y - etiqueta_altura + 15*mm, token_text)
        
        # Próxima coluna e incrementa contador
        coluna += 1
        total_etiquetas += 1
    
    # Adicionar página final com resumo simples
    c.showPage()
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(cor_texto)
    
    # Título centralizado
    titulo = "RESUMO DA GERAÇÃO DE ETIQUETAS"
    titulo_largura = c.stringWidth(titulo, "Helvetica-Bold", 14)
    c.drawString((largura_pagina - titulo_largura) / 2, altura_pagina/2 + 20*mm, titulo)
    
    # Linha horizontal
    c.setStrokeColor(cor_borda)
    c.setLineWidth(1)
    c.line(largura_pagina/4, altura_pagina/2 + 15*mm, 3*largura_pagina/4, altura_pagina/2 + 15*mm)
    
    # Informações do resumo
    c.setFont("Helvetica", 12)
    if evento:
        evento_texto = f"Evento: {evento.nome}"
        evento_largura = c.stringWidth(evento_texto, "Helvetica", 12)
        c.drawString((largura_pagina - evento_largura) / 2, altura_pagina/2, evento_texto)
        
        total_texto = f"Total de etiquetas: {total_etiquetas}"
        total_largura = c.stringWidth(total_texto, "Helvetica", 12)
        c.drawString((largura_pagina - total_largura) / 2, altura_pagina/2 - 10*mm, total_texto)
    else:
        total_texto = f"Total de etiquetas geradas: {total_etiquetas}"
        total_largura = c.stringWidth(total_texto, "Helvetica", 12)
        c.drawString((largura_pagina - total_largura) / 2, altura_pagina/2, total_texto)
    
    # Data de geração
    data_geracao = f"Gerado em: {datetime.utcnow().strftime('%d/%m/%Y às %H:%M')}"
    c.setFont("Helvetica", 10)
    data_largura = c.stringWidth(data_geracao, "Helvetica", 10)
    c.drawString((largura_pagina - data_largura) / 2, altura_pagina/2 - 30*mm, data_geracao)
    
    c.save()
    return pdf_path

def gerar_qr_code_inscricao(token):
    """Gera QR Code preto e branco com tamanho reduzido e boa qualidade"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=7,  # **Reduzi ainda mais**
        border=2,  # **Menos margem branca**
    )
    qr.add_data(token)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_path = os.path.join("static", "qrcodes", f"{token}.png")
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    img.save(img_path)
    return img_path

def obter_credenciais(token_file: str | None = None):
    """Retorna credenciais OAuth 2.0 para envio de e-mails sem interação."""
    token_file = token_file or os.getenv(TOKEN_FILE_ENV_VAR, TOKEN_FILE)

    creds = None
    token_data = os.getenv(TOKEN_ENV_VAR)
    if token_data:
        try:
            info = json.loads(token_data)
            creds = Credentials.from_authorized_user_info(info, SCOPES)
        except Exception as exc:  # pragma: no cover - log and continue
            logger.error("Erro ao carregar token do env %s: %s", TOKEN_ENV_VAR, exc)

    if not creds and token_file and os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as exc:  # pragma: no cover - log and continue
            logger.error("Erro ao ler token file %s: %s", token_file, exc)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            if token_file:
                with open(token_file, "w") as token:
                    token.write(creds.to_json())
        except Exception as exc:  # pragma: no cover - log and continue
            logger.error("Erro ao atualizar credenciais OAuth: %s", exc)
            return None

    if not creds or not creds.valid:
        logger.error(
            "Nenhuma credencial OAuth valida encontrada. Gere um refresh token manualmente e defina em %s ou salve no arquivo %s.",
            TOKEN_ENV_VAR,
            token_file,
        )
        return None

    return creds


@_profile
def enviar_email(destinatario, nome_participante, nome_oficina, assunto, corpo_texto,
                 anexo_path=None, corpo_html=None):
    """Wrapper para envio de e-mail utilizando o serviço definido em utils."""
    from utils import enviar_email as _send

    return _send(
        destinatario=destinatario,
        nome_participante=nome_participante,
        nome_oficina=nome_oficina,
        assunto=assunto,
        corpo_texto=corpo_texto,
        anexo_path=anexo_path,
        corpo_html=corpo_html,
    )
        

def gerar_certificado_personalizado(usuario, oficinas, total_horas, texto_personalizado, template_conteudo, cliente):
    """
    Gera um certificado personalizado em PDF para o usuário.

    Args:
        usuario: Objeto usuário com atributos id e nome
        oficinas: Lista de objetos oficina com atributo titulo e datas
        total_horas: Total de horas do evento
        texto_personalizado: Texto adicional personalizado 
        template_conteudo: Template com placeholders para o conteúdo
        cliente: Objeto cliente com atributos para imagens do certificado

    Returns:
        str: Caminho do arquivo PDF gerado
    """
    import os
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph, Frame
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

    # Configuração do arquivo de saída
    pdf_filename = f"certificado_evento_{usuario.id}.pdf"
    pdf_path = os.path.join("static/certificados", pdf_filename)

    # Criação do canvas com tamanho A4 paisagem
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    width, height = landscape(A4)

    # Determinar o conteúdo do certificado
    if template_conteudo:
        conteudo_final = template_conteudo
    elif cliente and cliente.texto_personalizado:
        conteudo_final = cliente.texto_personalizado
    else:
        conteudo_final = (
            "Certificamos que {NOME_PARTICIPANTE} participou das atividades {LISTA_OFICINAS}, "
            "com carga horária total de {CARGA_HORARIA} horas nas datas {DATAS_OFICINAS}. {TEXTO_PERSONALIZADO}"
        )

    # Extração das datas das oficinas
    datas_oficinas = ', '.join(
        ', '.join(data.strftime('%d/%m/%Y') for data in of.datas) if hasattr(of, 'datas') else ''
        for of in oficinas
    )

    # Substituição das variáveis no template
    conteudo_final = conteudo_final.replace("{NOME_PARTICIPANTE}", usuario.nome)\
                                   .replace("{CARGA_HORARIA}", str(total_horas))\
                                   .replace("{LISTA_OFICINAS}", ', '.join(of.titulo for of in oficinas))\
                                   .replace("{TEXTO_PERSONALIZADO}", texto_personalizado)\
                                   .replace("{DATAS_OFICINAS}", datas_oficinas)

    # ===== RENDERIZAÇÃO DO CERTIFICADO =====

    # 1. Imagem de fundo (ocupa toda a página)
    fundo_path = caminho_absoluto_arquivo(cliente.fundo_certificado)
    if fundo_path:
        fundo = ImageReader(fundo_path)
        c.drawImage(fundo, 0, 0, width=width, height=height)

    # 2. Título
    c.setFont("Helvetica-Bold", 24)
    titulo = "CERTIFICADO"
    titulo_largura = c.stringWidth(titulo, "Helvetica-Bold", 24)
    c.drawString((width - titulo_largura) / 2, height * 0.75, titulo)

    # 3. Texto principal (centralizado e justificado no meio da página)
    styles = getSampleStyleSheet()
    estilo_paragrafo = ParagraphStyle(
        'EstiloCertificado',
        parent=styles['Normal'],
        fontSize=14,
        leading=18,
        alignment=TA_JUSTIFY,
        spaceAfter=12
    )

    # Processando quebras de linha explícitas
    paragrafos = conteudo_final.split('\n')
    texto_formatado = '<br/>'.join(paragrafos)
    p = Paragraph(texto_formatado, estilo_paragrafo)

    margem_lateral = width * 0.15
    largura_texto = width - 2 * margem_lateral
    altura_texto = height * 0.3
    posicao_y_texto = height * 0.4

    frame = Frame(margem_lateral, posicao_y_texto, largura_texto, altura_texto, showBoundary=0)
    frame.addFromList([p], c)

    # 4. Logo (posicionada na parte inferior da página)
    logo_path = caminho_absoluto_arquivo(cliente.logo_certificado)
    if logo_path:
        logo_largura = 180
        logo_altura = 100
        margem_inferior = 50

        logo = ImageReader(logo_path)
        c.drawImage(logo, 
                   (width - logo_largura) / 2,
                   margem_inferior,
                   width=logo_largura, 
                   height=logo_altura,
                   preserveAspectRatio=True)

    # 5. Assinatura (posicionada acima da logo na parte inferior)
    assinatura_path = caminho_absoluto_arquivo(cliente.assinatura_certificado)
    if assinatura_path:
        assinatura_largura = 200
        assinatura_altura = 60

        if logo_path:
            assinatura_posicao_y = margem_inferior + logo_altura + 20
        else:
            assinatura_posicao_y = 30

        assinatura = ImageReader(assinatura_path)
        c.drawImage(
            assinatura,
            (width - assinatura_largura) / 2,
            assinatura_posicao_y,
            width=assinatura_largura,
            height=assinatura_altura,
            preserveAspectRatio=True,
            mask='auto'
        )

    c.save()
    return pdf_path



def gerar_certificados_pdf(oficina, inscritos, pdf_path):
    """
    Gera certificados em PDF para múltiplos inscritos de uma oficina.

    Args:
        oficina: Objeto oficina com atributos titulo, carga_horaria e cliente
        inscritos: Lista de objetos inscricao com atributo usuario
        pdf_path: Caminho onde o arquivo PDF será salvo

    Returns:
        str: Caminho do arquivo PDF gerado
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph, Frame
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

    # Obter o template de certificado
    template = CertificadoTemplate.query.filter_by(cliente_id=oficina.cliente_id, ativo=True).first()
    cliente = oficina.cliente

    # Determinar o conteúdo do certificado
    if template and template.conteudo:
        texto_certificado = template.conteudo
    elif cliente and cliente.texto_personalizado:
        texto_certificado = cliente.texto_personalizado
    else:
        texto_certificado = (
            "Certificamos que {NOME_PARTICIPANTE} participou da oficina {LISTA_OFICINAS}, "
            "com uma carga horária total de {CARGA_HORARIA} horas nas datas {DATAS_OFICINAS}."
        )
    
    datas_oficina = ', '.join(dia.data.strftime('%d/%m/%Y') for dia in sorted(oficina.dias, key=lambda x: x.data)) if hasattr(oficina, 'dias') and oficina.dias else ''

    # Inicializar o canvas
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    width, height = landscape(A4)

    # Criar estilos de parágrafo para texto formatado
    styles = getSampleStyleSheet()
    estilo_paragrafo = ParagraphStyle(
        'EstiloCertificado',
        parent=styles['Normal'],
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    # Gerar um certificado para cada inscrito
    for inscricao in inscritos:
        # Substituir as variáveis no template
        texto_final = (
            texto_certificado.replace("{NOME_PARTICIPANTE}", inscricao.usuario.nome)
                             .replace("{CARGA_HORARIA}", str(oficina.carga_horaria))
                             .replace("{LISTA_OFICINAS}", oficina.titulo)
                             .replace("{DATAS_OFICINAS}", datas_oficina)
        )

        # 1. Desenhar a imagem de fundo
        fundo_path = caminho_absoluto_arquivo(cliente.fundo_certificado)
        if fundo_path:
            fundo = ImageReader(fundo_path)
            c.drawImage(fundo, 0, 0, width=width, height=height)

        # 2. Adicionar título
        c.setFont("Helvetica-Bold", 24)
        titulo = "CERTIFICADO"
        titulo_largura = c.stringWidth(titulo, "Helvetica-Bold", 24)
        c.drawString((width - titulo_largura) / 2, height * 0.75, titulo)

        # 3. Texto principal do certificado (centralizado e formatado)
        paragrafos = texto_final.split('\n')
        texto_formatado = '<br/>'.join(paragrafos)
        p = Paragraph(texto_formatado, estilo_paragrafo)

        margem_lateral = width * 0.15
        largura_texto = width - 2 * margem_lateral
        altura_texto = height * 0.3
        posicao_y_texto = height * 0.4

        frame = Frame(margem_lateral, posicao_y_texto, largura_texto, altura_texto, showBoundary=0)
        frame.addFromList([p], c)

        # 4. Logo (posicionada na parte inferior da página)
        logo_path = caminho_absoluto_arquivo(cliente.logo_certificado)
        if logo_path:
            logo_largura = 180
            logo_altura = 100
            margem_inferior = 50

            logo = ImageReader(logo_path)
            c.drawImage(logo,
                      (width - logo_largura) / 2,
                      margem_inferior,
                      width=logo_largura,
                      height=logo_altura,
                      preserveAspectRatio=True)

        # 5. Assinatura
        assinatura_path = caminho_absoluto_arquivo(cliente.assinatura_certificado)
        if assinatura_path:
            assinatura_largura = 200
            assinatura_altura = 60

            if logo_path:
                assinatura_posicao_y = margem_inferior + logo_altura + 20
            else:
                assinatura_posicao_y = 30

            assinatura = ImageReader(assinatura_path)
            c.drawImage(
                assinatura,
                (width - assinatura_largura) / 2,
                assinatura_posicao_y,
                width=assinatura_largura,
                height=assinatura_altura,
                preserveAspectRatio=True,
                mask='auto'
            )

        c.showPage()

    c.save()
    return pdf_path

from flask import current_app


def caminho_absoluto_arquivo(imagem_relativa):
    """Resolve o caminho de uma imagem para um formato absoluto."""
    if not imagem_relativa:
        return None

    imagem_relativa = os.path.normpath(imagem_relativa)
    base_dir = current_app.root_path

    # Caminho absoluto fornecido
    if os.path.isabs(imagem_relativa):
        return imagem_relativa if os.path.exists(imagem_relativa) else None

    # Primeiro tenta o caminho relativo ao diretório da aplicação
    potencial = os.path.join(base_dir, imagem_relativa)
    if os.path.exists(potencial):
        return potencial

    # Fallback para dentro de "static"
    potencial = os.path.join(base_dir, 'static', imagem_relativa)
    return potencial if os.path.exists(potencial) else None

import os
import logging

# Configuração do logger para mensagens de pagamento
payment_logger = logging.getLogger("payment")
import mercadopago

token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
sdk = None
if token:
    try:
        sdk = mercadopago.SDK(token)
    except Exception as e:
        payment_logger.warning(f"⚠️ Erro ao inicializar SDK do Mercado Pago: {e}")
else:
    payment_logger.warning("⚠️ AVISO: MERCADOPAGO_ACCESS_TOKEN não definido. Funcionalidades de pagamento estarão indisponíveis.")

def criar_preferencia_pagamento(nome, email, descricao, valor, return_url):
    if sdk is None:
        payment_logger.warning(
            "Tentativa de criar preferência de pagamento com SDK não inicializado"
        )
        return None

    preference_data = {
        "payer": {"name": nome, "email": email, "last_name": nome},
        "items": [{
            "title": descricao,
            "description": descricao,
            "quantity": 1,
            "currency_id": "BRL",
            "unit_price": float(valor),
            "category_id": "evento"
        }],
        "back_urls": {
            "success": return_url,
            "failure": return_url,
            "pending": return_url
        }
    }
    auto_return = os.getenv("MP_AUTO_RETURN")
    if auto_return:
        preference_data["auto_return"] = auto_return
    try:
        preference_response = sdk.preference().create(preference_data)
        return preference_response["response"]["init_point"]
    except Exception as e:
        payment_logger.error(f"Erro ao criar preferência de pagamento: {e}")
        return None

# utils.py ou dentro da mesma função
def criar_preference_mp(usuario, tipo_inscricao, evento):
    sdk = mercadopago.SDK(os.getenv("MERCADOPAGO_ACCESS_TOKEN"))

    valor_com_taxa = float(preco_com_taxa(tipo_inscricao.preco))

    preference_data = {
        "items": [{
            "id": str(tipo_inscricao.id),
            "title": f"Inscrição – {tipo_inscricao.nome} – {evento.nome}",
            "description": f"Inscrição para {evento.nome} - {tipo_inscricao.nome}",
            "quantity": 1,
            "currency_id": "BRL",
            "unit_price": valor_com_taxa,    # ← preço já com taxa
            "category_id": "evento"
        }],
        "payer": {"email": usuario.email},
        "external_reference": str(usuario.id),
        "back_urls": {
            "success": external_url("mercadopago_routes.pagamento_sucesso"),
            "failure": external_url("mercadopago_routes.pagamento_falha"),
            "pending": external_url("mercadopago_routes.pagamento_pendente"),
        },
        "notification_url": external_url("mercadopago_routes.webhook_mp")
    }
    auto_return = os.getenv("MP_AUTO_RETURN")
    if auto_return:
        preference_data["auto_return"] = auto_return
    try:
        pref = sdk.preference().create(preference_data)
        return pref["response"]["init_point"]
    except Exception as e:
        payment_logger.error(f"Erro ao criar preferência MP: {e}")
        return None


# utils.py  (ou um novo arquivo helpers.py)
from functools import wraps
from flask_login import current_user
from flask import flash, redirect, url_for, request

def pagamento_necessario(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Todas as restrições de pagamento foram removidas
        # Agora todos os usuários podem realizar ações independentemente do status de pagamento
        return f(*args, **kwargs)
    return wrapper

import pytz
from datetime import datetime

def formatar_brasilia(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    brasilia = pytz.timezone("America/Sao_Paulo")
    return dt.astimezone(brasilia).strftime('%d/%m/%Y %H:%M:%S')

@_profile
def gerar_relatorio_necessidades(relatorio_dados, pdf_path=None):
    """Generate a PDF summarizing material needs for purchase planning."""
    from datetime import datetime
    from flask import send_file
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    import os
    import tempfile

    if not relatorio_dados:
        raise ValueError("relatorio_dados is required")

    if isinstance(relatorio_dados, dict) and "relatorio" in relatorio_dados:
        relatorio = relatorio_dados.get("relatorio") or {}
    else:
        relatorio = relatorio_dados or {}

    resumo = relatorio.get("resumo", {}) or {}
    itens = relatorio.get("itens_necessarios", []) or []

    if pdf_path:
        target_path = pdf_path
    else:
        filename = (
            "relatorio_necessidades_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        target_path = os.path.join(tempfile.gettempdir(), filename)

    doc = SimpleDocTemplate(
        target_path,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Relatorio de Necessidades",
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="NeedsTitle",
            parent=styles["Title"],
            fontSize=16,
            textColor=colors.HexColor("#1E88E5"),
            alignment=1,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="NeedsLabel",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#5A5A5A"),
            spaceAfter=4,
        )
    )

    story = [
        Paragraph(
            "Relatorio de Necessidades de Materiais",
            styles["NeedsTitle"],
        ),
        Paragraph(
            f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["NeedsLabel"],
        ),
        Spacer(1, 12),
    ]

    resumo_rows = [
        [
            "Total de materiais monitorados",
            str(resumo.get("total_materiais", 0)),
        ],
        [
            "Materiais esgotados",
            str(resumo.get("materiais_esgotados", 0)),
        ],
        [
            "Materiais com estoque baixo",
            str(resumo.get("materiais_estoque_baixo", 0)),
        ],
        [
            "Materiais com estoque normal",
            str(resumo.get("materiais_estoque_normal", 0)),
        ],
        [
            "Itens priorizados",
            str(resumo.get("total_itens_necessarios", 0)),
        ],
        [
            "Valor necessario",
            resumo.get("valor_total_necessario", 0),
        ],
    ]

    def format_currency(value):
        try:
            return "R$ " + (
                f"{float(value):,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
        except (TypeError, ValueError):
            return "R$ 0,00"

    resumo_rows[-1][1] = format_currency(resumo_rows[-1][1])

    resumo_table = Table(resumo_rows, colWidths=[9.2 * cm, 5.0 * cm])
    resumo_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E3F2FD")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0D47A1")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F5F5F5")],
                ),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BBDEFB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.extend([resumo_table, Spacer(1, 18)])

    story.append(
        Paragraph(
            "Itens priorizados para reposicao",
            styles["Heading2"],
        )
    )
    story.append(Spacer(1, 10))

    def format_number(value):
        try:
            number = float(value)
            return f"{number:,.0f}".replace(",", ".")
        except (TypeError, ValueError):
            return "-"

    itens_rows = [
        [
            "Material",
            "Polo",
            "Qtd atual",
            "Qtd minima",
            "Necessario",
            "Preco unitario",
            "Valor necessario",
        ]
    ]

    for item in itens:
        itens_rows.append(
            [
                item.get("material", "-"),
                item.get("polo", "-"),
                format_number(item.get("quantidade_atual")),
                format_number(item.get("quantidade_minima")),
                format_number(item.get("quantidade_necessaria")),
                format_currency(item.get("preco_unitario")),
                format_currency(item.get("valor_necessario")),
            ]
        )

    if len(itens_rows) > 1:
        itens_table = Table(
            itens_rows,
            colWidths=[
                4.5 * cm,
                3.0 * cm,
                2.1 * cm,
                2.1 * cm,
                2.3 * cm,
                2.7 * cm,
                3.0 * cm,
            ],
            repeatRows=1,
        )
        itens_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.25,
                        colors.HexColor("#B0BEC5"),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F1F5F9")],
                    ),
                    ("ALIGN", (2, 1), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(itens_table)
    else:
        story.append(
            Paragraph(
                "Nenhum item com necessidade de reposicao no momento.",
                styles["Normal"],
            )
        )

    doc.build(story)

    if pdf_path:
        return target_path

    return send_file(
        target_path,
        as_attachment=True,
        download_name=os.path.basename(target_path),
    )


def gerar_pdf_template(template_data):
    """Gera um PDF a partir dos dados estruturados do editor de certificados."""
    if not template_data:
        raise ValueError("Dados do template não fornecidos")

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape, portrait, A4
    from reportlab.lib import colors
    import qrcode

    orientation = (template_data.get('orientation') or 'landscape').lower()
    if orientation not in ('landscape', 'portrait'):
        orientation = 'landscape'

    base_width = 800 if orientation == 'landscape' else 600
    base_height = 600 if orientation == 'landscape' else 800

    page_size = landscape(A4) if orientation == 'landscape' else portrait(A4)
    page_width, page_height = page_size
    scale_x = page_width / base_width
    scale_y = page_height / base_height

    output_path = os.path.join(
        tempfile.gettempdir(), f"template_{uuid.uuid4().hex}.pdf"
    )

    pdf = canvas.Canvas(output_path, pagesize=page_size)
    elements = template_data.get('elements') or []
    temp_files = []

    for element in elements:
        element_type = (element.get('type') or '').lower()
        style = _parse_style_dict(element.get('style'))
        position = element.get('position') or {}
        properties = element.get('properties') or {}

        try:
            x_px = float(position.get('x', 0))
            y_px = float(position.get('y', 0))
        except (TypeError, ValueError):
            x_px = 0
            y_px = 0

        width_px = _parse_px(
            style.get('width') or properties.get('width'),
            default=150,
        )
        height_px = _parse_px(
            style.get('height') or properties.get('height'),
            default=50,
        )

        width = max(width_px * scale_x, 10)
        height = max(height_px * scale_y, 10)
        pdf_x = x_px * scale_x
        pdf_y = page_height - (y_px * scale_y) - height

        if element_type in ('text', 'variable'):
            font_size_px = _parse_px(style.get('font-size'), default=16)
            font_size = max(font_size_px * scale_y, 6)
            font_family = (style.get('font-family') or 'Helvetica').strip('"\' ')
            font_weight = (style.get('font-weight') or '').lower()
            font_name = 'Helvetica-Bold' if font_weight in ('bold', '700') else 'Helvetica'

            text_color = _parse_color(style.get('color'), colors.black)
            text_align = (style.get('text-align') or 'left').lower()
            raw_text = element.get('innerHTML') or properties.get('text') or ''
            text = _extract_text(raw_text)

            if not text:
                continue

            pdf.setFont(font_name, font_size)
            pdf.setFillColor(text_color)

            max_chars = max(int(width / max(font_size * 0.6, 1)), 1)
            lines = []
            for part in text.splitlines() or ['']:
                wrapped = textwrap.wrap(part, width=max_chars) or ['']
                lines.extend(wrapped)

            current_y = pdf_y + height - font_size
            leading = font_size * 1.2

            for line in lines:
                if text_align == 'center':
                    pdf.drawCentredString(pdf_x + width / 2, current_y, line)
                elif text_align == 'right':
                    pdf.drawRightString(pdf_x + width, current_y, line)
                else:
                    pdf.drawString(pdf_x, current_y, line)
                current_y -= leading

        elif element_type == 'signature':
            pdf.setStrokeColor(colors.black)
            pdf.setLineWidth(1)
            pdf.line(pdf_x, pdf_y + height / 2, pdf_x + width, pdf_y + height / 2)
            pdf.setFont('Helvetica', 10)
            pdf.drawCentredString(pdf_x + width / 2, pdf_y + height / 2 + 6, 'Assinatura')

        elif element_type == 'logo':
            src = properties.get('src') or _extract_image_src(element.get('innerHTML'))
            image_path = _resolve_image_path(src)
            if image_path:
                try:
                    pdf.drawImage(
                        image_path,
                        pdf_x,
                        pdf_y,
                        width=width,
                        height=height,
                        preserveAspectRatio=True,
                        anchor='sw',
                    )
                except Exception:
                    pdf.setStrokeColor(colors.HexColor('#E5E7EB'))
                    pdf.rect(pdf_x, pdf_y, width, height)
            else:
                pdf.setStrokeColor(colors.HexColor('#E5E7EB'))
                pdf.rect(pdf_x, pdf_y, width, height)

        elif element_type == 'qrcode':
            qr_content = properties.get('content') or _extract_text(element.get('innerHTML'))
            if qr_content:
                try:
                    qr_img = qrcode.make(qr_content)
                    temp_qr_path = os.path.join(
                        tempfile.gettempdir(), f"qr_{uuid.uuid4().hex}.png"
                    )
                    qr_img.save(temp_qr_path)
                    temp_files.append(temp_qr_path)
                    pdf.drawImage(
                        temp_qr_path,
                        pdf_x,
                        pdf_y,
                        width=width,
                        height=height,
                        preserveAspectRatio=True,
                        anchor='sw',
                    )
                except Exception:
                    pdf.setStrokeColor(colors.HexColor('#E5E7EB'))
                    pdf.rect(pdf_x, pdf_y, width, height)
            else:
                pdf.setStrokeColor(colors.HexColor('#E5E7EB'))
                pdf.rect(pdf_x, pdf_y, width, height)

        else:
            pdf.setStrokeColor(colors.HexColor('#E5E7EB'))
            pdf.rect(pdf_x, pdf_y, width, height)

    pdf.showPage()
    pdf.save()

    for temp_path in temp_files:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            logger.warning('Não foi possível remover arquivo temporário %s', temp_path)

    return output_path
