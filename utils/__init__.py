from .time_helpers import formatar_brasilia, determinar_turno
__all__ = ["formatar_brasilia", "determinar_turno"]


try:
    import requests  # Optional dependency
except Exception:  # pragma: no cover - used only in production
    requests = None
try:
    from reportlab.lib.units import inch
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
except Exception:  # pragma: no cover
    inch = mm = canvas = letter = landscape = colors = ImageReader = None
    A4 = None
import os
import base64
import json

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception:  # pragma: no cover
    Credentials = InstalledAppFlow = Request = build = HttpError = None
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
try:
    import qrcode
except Exception:  # pragma: no cover
    qrcode = None
from models import CertificadoTemplate, Inscricao, Evento
from models.user import Usuario
import logging



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
from models.user import Cliente
from flask import current_app, request
from utils.taxa_service import calcular_taxa_cliente

def preco_com_taxa(base, cliente_id=None):
    """
    Recebe o preço digitado pelo cliente (Decimal, str ou float)
    e devolve o valor acrescido do percentual configurado,
    considerando possíveis taxas diferenciadas por cliente.
    
    Args:
        base: preço base do item (Decimal, str ou float)
        cliente_id: ID opcional do cliente para considerar taxa diferenciada
        
    Returns:
        Decimal: Valor com taxa aplicada
    """
    if not base:
        try:
            return Decimal(str(base)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        except Exception:
            return Decimal("0").quantize(Decimal("0.01"), ROUND_HALF_UP)

    logger = logging.getLogger("preco_com_taxa")
    logger.debug(f"Calculando preço com taxa - base: {base}, cliente_id: {cliente_id}")
    
    try:
        # Converter base para Decimal de forma segura
        try:
            base = Decimal(str(base)) 
            logger.debug(f"Preço base convertido para Decimal: {base}")
        except Exception as e:
            logger.error(f"Erro ao converter preço base para Decimal: {str(e)}")
            # Fallback para um valor padrão se houver erro
            base = Decimal('0')
        
        # Obter taxa geral do sistema
        try:
            cfg = Configuracao.query.first()
            taxa_geral = float(cfg.taxa_percentual_inscricao or 0) if cfg else 0.0
            logger.debug(f"Taxa geral obtida: {taxa_geral}%")
        except Exception as e:
            logger.error(f"Erro ao obter taxa geral: {str(e)}")
            taxa_geral = 0.0
        
        # Se temos um cliente_id, verifica se tem taxa diferenciada
        perc = Decimal(str(taxa_geral))  # valor padrão
        if cliente_id:
            try:
                logger.debug(f"Buscando cliente ID={cliente_id}")
                cliente = Cliente.query.get(cliente_id)
                if cliente:
                    logger.debug(f"Cliente encontrado: {cliente.nome}")
                    resultado_taxa = calcular_taxa_cliente(cliente, taxa_geral)
                    taxa_aplicada = resultado_taxa["taxa_aplicada"]
                    logger.debug(f"Taxa aplicada após cálculo: {taxa_aplicada}")
                    perc = Decimal(str(taxa_aplicada))
                else:
                    logger.warning(f"Cliente ID={cliente_id} não encontrado, usando taxa geral")
            except Exception as e:
                logger.exception(f"Erro ao processar taxa diferenciada: {str(e)}")
        
        # Calcular preço final com taxa
        logger.debug(f"Percentual final da taxa: {perc}%")
        valor = base * (Decimal('1') + perc/Decimal('100'))
        resultado = valor.quantize(Decimal("0.01"), ROUND_HALF_UP)
        logger.debug(f"Preço final com taxa: {resultado}")
        return resultado
        
    except Exception as e:
        logger.exception(f"Erro inesperado ao calcular preço com taxa: {str(e)}")
        # Em caso de erro, retorna o preço base sem taxa
        try:
            return Decimal(str(base)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        except:
            return Decimal('0').quantize(Decimal("0.01"), ROUND_HALF_UP)


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


def enviar_email(destinatario, nome_participante, nome_oficina, assunto, corpo_texto,
                 anexo_path=None, corpo_html=None, template_path=None,
                 template_context=None):
    """Envia um e-mail utilizando o EmailService unificado.

    Esta função agora usa o novo EmailService que suporta Mailjet e SMTP fallback,
    com logs detalhados e validação de templates.
    """
    from services.email_service import email_service
    
    try:
        logger.info(f"Iniciando envio de email legacy para: {destinatario}")
        
        # Usar o novo EmailService unificado
        resultado = email_service.enviar_email_unificado(
            destinatario=destinatario,
            nome_participante=nome_participante,
            nome_oficina=nome_oficina,
            assunto=assunto,
            corpo_texto=corpo_texto,
            anexo_path=anexo_path,
            corpo_html=corpo_html,
            template_path=template_path,
            template_context=template_context
        )
        
        if resultado.get('success', False):
            logger.info("✅ E-mail enviado com sucesso para %s", destinatario)
            return True
        else:
            logger.error("❌ Falha ao enviar email para %s: %s", destinatario, resultado.get('error'))
            return False
            
    except Exception as e:
        logger.error("❌ Erro ao enviar email para %s: %s", destinatario, e, exc_info=True)
        return False
        

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
    from reportlab.lib.enums import TA_JUSTIFY

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
    from reportlab.lib.enums import TA_CENTER

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

    if os.path.isabs(imagem_relativa):
        return imagem_relativa if os.path.exists(imagem_relativa) else None

    potencial = os.path.join(base_dir, imagem_relativa)
    if os.path.exists(potencial):
        return potencial

    potencial = os.path.join(base_dir, 'static', imagem_relativa)
    return potencial if os.path.exists(potencial) else None

import mercadopago
import os

token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
sdk = None
if token:
    try:
        sdk = mercadopago.SDK(token)
    except Exception as e:
        logger.warning("⚠️ Erro ao inicializar SDK do Mercado Pago: %s", e)
else:
    logger.warning(
        "⚠️ AVISO: MERCADOPAGO_ACCESS_TOKEN não definido. Funcionalidades de pagamento estarão indisponíveis."
    )

def criar_preferencia_pagamento(nome, email, descricao, valor, return_url):
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
    preference_response = sdk.preference().create(preference_data)
    return preference_response["response"]["init_point"]

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
    pref = sdk.preference().create(preference_data)
    return pref["response"]["init_point"]


# utils.py  (ou um novo arquivo helpers.py)
from functools import wraps
from flask import url_for, request, current_app
def external_url(endpoint: str, **values) -> str:
    """Gera URL absoluta usando APP_BASE_URL se definido."""
    base = os.getenv("APP_BASE_URL")
    if base:
        # Garantir que a URL base seja válida, adicionando https:// se necessário
        if not base.startswith(('http://', 'https://')):
            base = 'https://' + base
        return base.rstrip("/") + url_for(endpoint, _external=False, **values)
    
    # Certificar de que temos um host válido se _external=True
    if not request.host:
        # Fallback para uma URL completa usando o SERVER_NAME configurado
        server_name = current_app.config.get('SERVER_NAME', 'localhost:5000')
        scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'https')  # Padronizando para HTTPS
        path = url_for(endpoint, _external=False, **values)
        return f"{scheme}://{server_name}{path}"
    
    try:
        # Garantir que a URL gerada seja absoluta
        url = url_for(endpoint, _external=True, **values)
        if not url.startswith(('http://', 'https://')):
            # Se ainda não for absoluta, aplicar o protocolo HTTPS
            url = f"https://{request.host}{url if url.startswith('/') else '/' + url}"
        return url
    except Exception as e:
        # Fallback em caso de erro na geração da URL
        logging.exception(f"Erro ao gerar external_url para {endpoint}: {e}")
        server_name = current_app.config.get('SERVER_NAME', 'localhost:5000')
        path = url_for(endpoint, _external=False, **values)
        return f"https://{server_name}{path}"

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

from pytz import timezone

def brasilia_filter(value):
    if value:
        return value.astimezone(timezone("America/Sao_Paulo")).strftime('%d/%m/%Y %H:%M')
    return ""
