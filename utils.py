import requests
import qrcode
import os
from reportlab.lib.units import inch




# ReportLab para PDFs
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

def gerar_comprovante_pdf(usuario, oficina, inscricao):
    pdf_filename = f"comprovante_{usuario.id}_{oficina.id}.pdf"
    pdf_path = os.path.join("static/comprovantes", pdf_filename)
    os.makedirs("static/comprovantes", exist_ok=True)

    # Gera o QR Code da inscrição (certifique-se de ter a função gerar_qr_code_inscricao importada)
    qr_path = gerar_qr_code_inscricao(inscricao.qr_code_token)
    
    # Configura o PDF
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    #
    # 1) Faixa colorida no topo (Ex.: cor azul)
    #
    c.setFillColor(colors.HexColor("#023E8A"))
    c.rect(0, height - 80, width, 80, fill=True, stroke=False)

    # Título em destaque
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.white)
    c.drawCentredString(width / 2, height - 50, "Comprovante de Inscrição")

    #
    # 2) Área principal (cor clara, p.ex. cinza-claro)
    #
    c.setFillColor(colors.whitesmoke)
    c.rect(0, 0, width, height - 80, fill=True, stroke=False)

    #
    # 3) Informações do participante e da oficina
    #
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 14)

    # Posição inicial do texto
    y_position = height - 120
    linhas_info = [
        f"Nome: {usuario.nome}",
        f"CPF: {usuario.cpf}",
        f"E-mail: {usuario.email}",
        f"Oficina: {oficina.titulo}"
    ]
    for linha in linhas_info:
        c.drawString(1 * inch, y_position, linha)
        y_position -= 20

    #
    # 4) Destaque para o QR Code
    #
    # Criar um box (retângulo) branco para destacar
    box_width = 120
    box_height = 120
    box_x = width - (box_width + 1 * inch)
    box_y = y_position - 10

    c.setFillColor(colors.white)
    c.rect(box_x, box_y, box_width, box_height, fill=True, stroke=False)

    # Desenha o QR Code dentro do retângulo
    qr_img = ImageReader(qr_path)
    # Margem de 10 px para o QR dentro do box
    c.drawImage(qr_img, box_x + 10, box_y + 10, width=box_width - 20, height=box_height - 20)

    #
    # 5) Espaço para assinatura
    #
    y_position -= 60
    c.setFont("Helvetica", 12)
    c.setStrokeColor(colors.gray)
    c.line(1 * inch, y_position, 4 * inch, y_position)
    c.drawString(1 * inch, y_position - 15, "Assinatura / Carimbo")

    #
    # Finaliza
    #
    c.showPage()
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
