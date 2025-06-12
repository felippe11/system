from .time_helpers import formatar_brasilia
__all__ = ["formatar_brasilia"]


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
from models import CertificadoTemplate, Oficina, Usuario, Cliente, Inscricao
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

# Configuração de logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Escopo necessário para envio de e-mails
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
# Configuracoes de OAuth
TOKEN_FILE = "token.json"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

from decimal import Decimal, ROUND_HALF_UP
from models import Configuracao

def preco_com_taxa(base):
    """
    Recebe o preço digitado pelo cliente (Decimal, str ou float)
    e devolve o valor acrescido do percentual configurado.
    """
    base = Decimal(str(base))
    cfg  = Configuracao.query.first()
    perc = Decimal(str(cfg.taxa_percentual_inscricao or 0))
    valor = base * (1 + perc/100)
    # duas casas, arredondamento comercial
    return valor.quantize(Decimal("0.01"), ROUND_HALF_UP)


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
    Gera um PDF com etiquetas modernas contendo Nome, ID, QR Code e informações do evento.
    Se evento_id for fornecido, apenas gera etiquetas para os usuários inscritos nesse evento.
    """
    
    # Configurações de layout
    etiqueta_largura = 85 * mm
    etiqueta_altura = 54 * mm
    margem_esquerda = 15 * mm
    margem_superior = 20 * mm
    margem_inferior = 15 * mm
    espacamento_x = 10 * mm
    espacamento_y = 8 * mm
    
    # Paleta de cores moderna
    cor_primaria = colors.HexColor("#3498DB")  # Azul moderno
    cor_texto_escuro = colors.HexColor("#2C3E50")  # Quase preto
    cor_texto_claro = colors.HexColor("#ECF0F1")  # Branco off-white
    cor_detalhe = colors.HexColor("#1ABC9C")  # Verde-água
    
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
    
    # Documento em landscape
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    largura_pagina, altura_pagina = landscape(A4)
    
    # Calcular quantidade de colunas/linhas por página
    max_colunas = int((largura_pagina - margem_esquerda * 2) // (etiqueta_largura + espacamento_x))
    espaco_vertical = altura_pagina - margem_superior - margem_inferior
    max_linhas = int(espaco_vertical // (etiqueta_altura + espacamento_y))
    
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
    
    # Cabeçalho minimalista no topo da página
    def desenhar_cabecalho():
        # Retângulo fino na parte superior
        c.setFillColor(cor_primaria)
        c.rect(0, altura_pagina - 15*mm, largura_pagina, 8*mm, fill=1, stroke=0)
        
        # Texto do cabeçalho
        c.setFillColor(cor_texto_claro)
        c.setFont("Helvetica-Bold", 11)
        
        if evento:
            # Limitar o tamanho do nome do evento no cabeçalho
            nome_evento = evento.nome
            if len(nome_evento) > 40:
                nome_evento = nome_evento[:37] + "..."
            c.drawString(margem_esquerda, altura_pagina - 10*mm, f"ETIQUETAS • {nome_evento}")
        else:
            c.drawString(margem_esquerda, altura_pagina - 10*mm, f"ETIQUETAS • CLIENTE {cliente_id}")
        
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
        
        # Design moderno com faixa lateral colorida
        # Base branca com cantos arredondados suaves
        c.setFillColor(colors.white)
        c.roundRect(x, y - etiqueta_altura, etiqueta_largura, etiqueta_altura, 2*mm, fill=1, stroke=0)
        
        # Faixa vertical colorida à esquerda (design moderno)
        c.setFillColor(cor_primaria)
        c.rect(x, y - etiqueta_altura, 5*mm, etiqueta_altura, fill=1, stroke=0)
        
        # Linha fina horizontal abaixo do nome para separação visual
        c.setStrokeColor(cor_detalhe)
        c.setLineWidth(0.5)
        linha_y = y - 14*mm
        c.line(x + 12*mm, linha_y, x + etiqueta_largura - 7*mm, linha_y)
        
        # Nome do usuário (com tipografia moderna)
        nome = usuario.nome
        if len(nome) > 22:  # Limite um pouco menor para nomes muito compridos
            nome = nome[:20] + "..."
        
        c.setFillColor(cor_texto_escuro)
        c.setFont("Helvetica-Bold", 14)
        # Alinhado à esquerda com recuo após a faixa colorida
        nome_x = x + 12*mm
        nome_y = y - 10*mm
        c.drawString(nome_x, nome_y, nome)
        
        # ID com estilo mais discreto e moderno
        token_curto = inscricao.qr_code_token[:6] if inscricao and inscricao.qr_code_token else ""
        
        # ID combinado com início do token para identificação rápida
        if token_curto:
            id_str = f"#{usuario.id} • {token_curto}"
        else:
            id_str = f"#{usuario.id}"
            
        c.setFont("Helvetica", 9)
        c.setFillColor(cor_primaria)
        c.drawString(nome_x, nome_y - 8*mm, id_str)
        
        # Adicionar informações do evento à etiqueta
        if evento:
            # Formatação da data de início do evento
            data_evento = ""
            if evento.data_inicio:
                data_evento = evento.data_inicio.strftime('%d/%m/%Y')
                if evento.data_fim and evento.data_fim != evento.data_inicio:
                    data_evento += f" - {evento.data_fim.strftime('%d/%m/%Y')}"
            
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(cor_detalhe)
            evento_str = evento.nome
            if len(evento_str) > 28:  # Limite para o nome do evento
                evento_str = evento_str[:26] + "..."
            c.drawString(nome_x, nome_y - 16*mm, evento_str)
            
            if data_evento:
                c.setFont("Helvetica", 7)
                c.setFillColor(cor_texto_escuro)
                c.drawString(nome_x, nome_y - 22*mm, data_evento)
        
        # QR Code com posicionamento e tamanho otimizados
        if inscricao and inscricao.qr_code_token:
            qr_size = 28 * mm  # Tamanho um pouco maior
            qr_code_path = gerar_qr_code_inscricao(inscricao.qr_code_token)
            
            try:
                qr_image = ImageReader(qr_code_path)
                # Posicionado à direita para design assimétrico moderno
                qr_x = x + etiqueta_largura - qr_size - 7*mm
                qr_y = y - etiqueta_altura + 6*mm  # Mais próximo da base
                
                c.drawImage(qr_image, qr_x, qr_y, qr_size, qr_size)
                
                # Pequeno indicador "SCAN" acima do QR
                c.setFont("Helvetica-Bold", 7)
                c.setFillColor(cor_detalhe)
                c.drawString(qr_x, qr_y + qr_size + 2*mm, "SCAN")
            except Exception:
                # Fallback de texto se não for possível desenhar o QR
                c.setFont("Helvetica", 8)
                c.setFillColor(colors.gray)
                c.drawString(x + 12*mm, (y - etiqueta_altura) + 10*mm,
                           f"QR: {inscricao.qr_code_token[:10]}...")
        
        # Próxima coluna e incrementa contador
        coluna += 1
        total_etiquetas += 1
    
    # Adicionar página final com resumo
    c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(cor_texto_escuro)
    
    resumo_texto = f"Total de etiquetas geradas: {total_etiquetas}"
    if evento:
        resumo_texto = f"Etiquetas geradas para o evento: {evento.nome}\n\n{resumo_texto}"
    
    c.drawString(largura_pagina/2 - 80*mm, altura_pagina/2, resumo_texto)
    
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
            if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
                logger.error("Variaveis GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET nao estao definidas.")
                return None

            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                    }
                },
                SCOPES,
                redirect_uri="https://appfiber.com.br/",
            )

            # Exibir o link de autenticacao manualmente
            auth_url, _ = flow.authorization_url(prompt="consent")
            print(f"\ud83d\udd17 Acesse este link para autenticacao manual:\n{auth_url}")

            # Executar autenticacao manual (esperar codigo do usuario)
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

def caminho_absoluto_arquivo(imagem_relativa):
    """Retorna o caminho absoluto corrigido para leitura de imagem"""
    if not imagem_relativa:
        return None

    # Evita duplicar 'static/static/...'
    if imagem_relativa.startswith('static/'):
        return imagem_relativa
    return os.path.join('static', imagem_relativa)

import mercadopago
import os

token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
sdk = None
if token:
    try:
        sdk = mercadopago.SDK(token)
    except Exception as e:
        print(f"⚠️ Erro ao inicializar SDK do Mercado Pago: {e}")
else:
    print("⚠️ AVISO: MERCADOPAGO_ACCESS_TOKEN não definido. Funcionalidades de pagamento estarão indisponíveis.")

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
        },
        "auto_return": "approved"
    }
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
            "success": url_for("mercadopago_routes.pagamento_sucesso", _external=True),
            "failure": url_for("mercadopago_routes.pagamento_falha", _external=True),
            "pending": url_for("mercadopago_routes.pagamento_pendente", _external=True)
        },
        "auto_return": "approved",
        "notification_url": url_for("mercadopago_routes.webhook_mp", _external=True)
    }
    pref = sdk.preference().create(preference_data)
    return pref["response"]["init_point"]


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

from pytz import timezone

def brasilia_filter(value):
    if value:
        return value.astimezone(timezone("America/Sao_Paulo")).strftime('%d/%m/%Y %H:%M')
    return ""
