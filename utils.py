import requests
from reportlab.lib.units import inch
import os
import base64
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
from models import Oficina, Usuario, Cliente, Inscricao
from flask_mail import Message
from extensions import mail
import logging

# ReportLab para PDFs
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Configuração de logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Escopo necessário para envio de e-mails
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
# Caminhos dos arquivos JSON
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

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


def gerar_etiquetas_pdf(cliente_id):
    """Gera um PDF com etiquetas elegantes para os usuários vinculados a um cliente."""
    
    # Configurações de layout
    etiqueta_largura = 85 * mm  # Ligeiramente menor para melhor espaçamento
    etiqueta_altura = 54 * mm   # Proporção mais agradável
    margem_esquerda = 15 * mm   # Margens maiores para melhor espaço em branco
    margem_superior = 20 * mm
    margem_inferior = 15 * mm
    espacamento_x = 10 * mm     # Mais espaço entre as etiquetas
    espacamento_y = 8 * mm
    
    # Esquema de cores suave
    cor_header = colors.HexColor("#2C3E50")  # Azul escuro elegante
    cor_fundo = colors.white                 # Fundo branco para clareza
    cor_texto = colors.HexColor("#34495E")   # Texto escuro mas não preto
    cor_borda = colors.HexColor("#BDC3C7")   # Borda cinza claro
    
    pdf_filename = f"etiquetas_cliente_{cliente_id}.pdf"
    pdf_path = os.path.join("static", "etiquetas", pdf_filename)
    os.makedirs("static/etiquetas", exist_ok=True)
    
    # Configurar documento em landscape
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    largura_pagina, altura_pagina = landscape(A4)
    
    # Calcular quantidade máxima de etiquetas por página
    max_colunas = int((largura_pagina - margem_esquerda * 2) // (etiqueta_largura + espacamento_x))
    espaco_vertical = altura_pagina - margem_superior - margem_inferior
    max_linhas = int(espaco_vertical // (etiqueta_altura + espacamento_y))
    
    # Buscar usuários do cliente
    usuarios = Usuario.query.filter_by(cliente_id=cliente_id).all()
    
    if not usuarios:
        return None
    
    linha = 0
    coluna = 0
    
    # Adicionar informações do documento
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#7F8C8D"))
    c.drawString(margem_esquerda, altura_pagina - 10*mm, f"Etiquetas - Cliente: {cliente_id}")
    c.drawRightString(largura_pagina - margem_esquerda, altura_pagina - 10*mm, f"Gerado em: {datetime.utcnow().strftime('%d/%m/%Y')}")
    
    for usuario in usuarios:
        if coluna >= max_colunas:
            coluna = 0
            linha += 1
        
        if linha >= max_linhas:
            c.showPage()
            # Repetir cabeçalho em cada página
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.HexColor("#7F8C8D"))
            c.drawString(margem_esquerda, altura_pagina - 10*mm, f"Etiquetas - Cliente: {cliente_id}")
            c.drawRightString(largura_pagina - margem_esquerda, altura_pagina - 10*mm, f"Gerado em: {datetime.utcnow().strftime('%d/%m/%Y')}")
            linha = 0
            coluna = 0
        
        # Calcular posição
        x = margem_esquerda + coluna * (etiqueta_largura + espacamento_x)
        y = altura_pagina - margem_superior - linha * (etiqueta_altura + espacamento_y)
        
        # Fundo da etiqueta com sombra sutil
        # Primeiro desenha uma sombra cinza claro
        c.setFillColor(colors.HexColor("#EAEAEA"))
        c.roundRect(x + 1.5*mm, y - etiqueta_altura - 1.5*mm, 
                    etiqueta_largura, etiqueta_altura, 4*mm, fill=1, stroke=0)
        
        # Depois desenha a etiqueta principal
        c.setFillColor(cor_fundo)
        c.roundRect(x, y - etiqueta_altura, 
                    etiqueta_largura, etiqueta_altura, 4*mm, fill=1, stroke=0)
        
        # Header da etiqueta com gradiente
        header_height = 18 * mm
        
        # Desenhar a barra superior em azul
        c.setFillColor(cor_header)
        c.roundRect(x, y - etiqueta_altura, etiqueta_largura, header_height, 
                   4*mm, fill=1, stroke=0)
        
        # Arredondar apenas cantos superiores do header
        c.setFillColor(cor_header)
        c.roundRect(x, y - etiqueta_altura + header_height - 4*mm, 
                    etiqueta_largura, 4*mm, 0, fill=1, stroke=0)
        
        # Nome e cargo no header
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        
        # Limitar nome para caber
        nome = usuario.nome
        if len(nome) > 20:
            nome = nome[:18] + '...'
            
        # Centralizar nome
        nome_width = c.stringWidth(nome, "Helvetica-Bold", 14)
        nome_x = x + (etiqueta_largura - nome_width) / 2
        c.drawString(nome_x, y - etiqueta_altura + header_height - 8*mm, nome)
        
        # Tipo de usuário abaixo do nome
        tipo_usuario = usuario.tipo.capitalize()
        c.setFont("Helvetica", 10)
        tipo_width = c.stringWidth(tipo_usuario, "Helvetica", 10)
        tipo_x = x + (etiqueta_largura - tipo_width) / 2
        c.drawString(tipo_x, y - etiqueta_altura + header_height - 12*mm, tipo_usuario)
        
        # Corpo da etiqueta
        corpo_y = y - etiqueta_altura + header_height
        
        # Ícone e localização centralizada
        c.setFillColor(cor_texto)
        c.setFont("Helvetica-Bold", 12)
        
        cidade = "N/A"
        estado = "N/A"
        
        if usuario.cidades and usuario.estados:
            cidades_list = usuario.cidades.split(",")
            estados_list = usuario.estados.split(",")
            
            if cidades_list and len(cidades_list) > 0:
                cidade = cidades_list[0].strip()
            if estados_list and len(estados_list) > 0:
                estado = estados_list[0].strip()
        
        local_text = f"{cidade}, {estado}"
        if len(local_text) > 25:
            local_text = local_text[:23] + "..."
            
        local_width = c.stringWidth(local_text, "Helvetica-Bold", 12)
        local_x = x + (etiqueta_largura - local_width) / 2
        
        # Ícone de localização
        c.setFont("Helvetica", 12)
        c.drawString(local_x - 5*mm, corpo_y + 15*mm, "📍")
        
        # Texto de localização
        c.setFont("Helvetica-Bold", 12)
        c.drawString(local_x, corpo_y + 15*mm, local_text)
        
        # QR Code centralizado
        inscricao = Inscricao.query.filter_by(usuario_id=usuario.id).first()
        if inscricao and inscricao.qr_code_token:
            qr_size = 26 * mm  # Tamanho ideal
            qr_code_path = gerar_qr_code_inscricao(inscricao.qr_code_token)
            
            try:
                qr_image = ImageReader(qr_code_path)
                c.drawImage(qr_image, 
                            x + (etiqueta_largura - qr_size) / 2,  # Centralizar
                            corpo_y - 7*mm - qr_size,  # Posicionado na parte inferior
                            qr_size, qr_size)
            except Exception as e:
                # Fallback se houver problema com a imagem
                c.setFont("Helvetica", 8)
                c.setFillColor(colors.gray)
                c.drawCentredString(x + etiqueta_largura/2, 
                                   corpo_y - 10*mm,
                                   f"QR Code: {inscricao.qr_code_token[:10]}...")
        
        # Borda elegante
        c.setStrokeColor(cor_borda)
        c.setLineWidth(0.5*mm)
        c.roundRect(x, y - etiqueta_altura, etiqueta_largura, etiqueta_altura, 
                    4*mm, stroke=1, fill=0)
        
        # Adiciona ID da pessoa em fonte pequena na parte inferior
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.gray)
        c.drawCentredString(x + etiqueta_largura/2, y - etiqueta_altura + 3*mm, f"ID: {usuario.id}")
        
        coluna += 1
    
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

def obter_credenciais():
    """Autentica e retorna credenciais OAuth 2.0 para envio de e-mails"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES,
                redirect_uri="https://appfiber.com.br/"
            )

            # Exibir o link de autenticação manualmente
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"🔗 Acesse este link para autenticação manual:\n{auth_url}")

            # Executar autenticação manual (esperar código do usuário)
            creds = flow.run_console()

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def enviar_email(destinatario, nome_participante, nome_oficina, assunto, corpo_texto, anexo_path=None):
    """Envia um e-mail personalizado via API do Gmail usando OAuth 2.0"""
    creds = obter_credenciais()

    if not creds or not creds.valid:
        logger.error("❌ Erro ao obter credenciais OAuth 2.0.")
        return

    try:
        # Criar o serviço Gmail API
        service = build("gmail", "v1", credentials=creds)

        remetente = "seuemail@gmail.com"  # Substitua pelo seu e-mail

        # Criar corpo do e-mail em HTML
        corpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #2C3E50; text-align: center;">Confirmação de Inscrição</h2>
                <p>Olá, <b>{nome_participante}</b>!</p>
                <p>Você se inscreveu com sucesso na oficina <b>{nome_oficina}</b>.</p>
                <p>Aguardamos você no evento!</p>
                
                <div style="padding: 15px; background-color: #f4f4f4; border-left: 5px solid #3498db;">
                    <p><b>Detalhes da Oficina:</b></p>
                    <p><b>Nome:</b> {nome_oficina}</p>
                </div>

                <p>Caso tenha dúvidas, entre em contato conosco.</p>
                <p style="text-align: center;">
                    <b>Equipe Organizadora</b>
                </p>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart()
        msg["From"] = remetente
        msg["To"] = destinatario
        msg["Subject"] = assunto

        # Adiciona corpo em texto puro e HTML
        msg.attach(MIMEText(corpo_texto, "plain"))
        msg.attach(MIMEText(corpo_html, "html"))

        # Adiciona anexo se existir
        if anexo_path:
            with open(anexo_path, "rb") as anexo:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(anexo.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(anexo_path)}")
                msg.attach(part)

        # Converte a mensagem para base64
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        message = {"raw": raw_message}

        # Enviar e-mail via Gmail API
        enviado = service.users().messages().send(userId="me", body=message).execute()
        logger.info(f"✅ E-mail enviado com sucesso para {destinatario}! ID: {enviado['id']}")

    except HttpError as error:
        logger.error(f"❌ ERRO ao enviar e-mail: {error}", exc_info=True)
