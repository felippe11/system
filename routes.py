from flask import Flask, Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db  # Importa corretamente o banco de dados
from models import Usuario, Oficina, Inscricao, OficinaDia, Checkin
from utils import obter_estados, obter_cidades, gerar_qr_code  # Funções auxiliares
from datetime import datetime
import os
import requests
from extensions import db, login_manager  # Importa login_manager corretamente
from flask import session
import pandas as pd
from flask import request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from models import Oficina  # Modelo atualizado da oficina
from models import Configuracao 

# ReportLab para PDFs
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import qrcode

# Registrar a fonte personalizada
pdfmetrics.registerFont(TTFont("AlexBrush", "AlexBrush-Regular.ttf"))

routes = Blueprint("routes", __name__)
app = Flask(__name__)

@routes.route('/')
def home():
    return render_template('index.html')

# Registrar as rotas corretamente no app
def register_routes(app):
    app.register_blueprint(routes)


# ===========================
# ROTA DE HOME
# ===========================


# ===========================
# CADASTRO DE PARTICIPANTE
# ===========================
@routes.route('/cadastro_participante', methods=['GET', 'POST'])
def cadastro_participante():
    alert = None  # Inicializa o alerta como None

    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        senha = request.form.get('senha')
        formacao = request.form.get('formacao')

        print(f"📌 Recebido: Nome={nome}, CPF={cpf}, Email={email}, Formação={formacao}, Senha={senha}")
        
        # 🔍 Verifica se o e-mail já existe no banco
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash('Erro: Este e-mail já está cadastrado!', 'danger')
            return redirect(url_for('routes.cadastro_participante'))

        # Verificar se o CPF já existe
        usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
        if usuario_existente:
            alert = {"category": "danger", "message": "CPF já está sendo usado por outro usuário!"}
        elif not senha:
            alert = {"category": "danger", "message": "A senha é obrigatória!"}
        else:
            # Criar novo usuário com senha criptografada
            novo_usuario = Usuario(
                nome=nome,
                cpf=cpf,
                email=email,
                senha=generate_password_hash(senha),
                formacao=formacao,
                tipo='participante'
            )
            try:
                db.session.add(novo_usuario)
                db.session.commit()
                alert = {"category": "success", "message": "Cadastro realizado com sucesso!"}
                return redirect(url_for('routes.login'))
  # Redireciona após sucesso
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao cadastrar usuário: {e}")
                alert = {"category": "danger", "message": "Erro ao cadastrar. Tente novamente!"}

    return render_template('cadastro_participante.html', alert=alert)






# ===========================
# GESTÃO DE USUÁRIOS
# ===========================
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario:
            print(f"Usuário encontrado: {usuario.email}, Tipo: {usuario.tipo}")  # Debug
        else:
            print("Usuário não encontrado.")  # Debug

        if usuario and check_password_hash(usuario.senha, senha):
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')

            if usuario.tipo == 'admin':
                return redirect(url_for('routes.dashboard'))  # Redireciona para admin
            else:
                return redirect(url_for('routes.dashboard_participante'))  # Redireciona para participante
        else:
            flash('E-mail ou senha incorretos!', 'danger')

    return render_template('login.html')



@routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'info')
    return redirect(url_for('routes.home'))

# ===========================
# DASHBOARD - ADMIN & PARTICIPANTE
# ===========================
@routes.route('/dashboard')
@login_required
def dashboard():
    if current_user.tipo == 'admin':
        oficinas = Oficina.query.all()
        oficinas_com_inscritos = []

        # 🔹 Buscar a configuração do check-in global no banco de dados
        configuracao = Configuracao.query.first()
        permitir_checkin_global = configuracao.permitir_checkin_global if configuracao else False

        for oficina in oficinas:
            dias = OficinaDia.query.filter_by(oficina_id=oficina.id).all()
            dias_formatados = [dia.data.strftime('%d/%m/%Y') for dia in dias]

            inscritos = Inscricao.query.filter_by(oficina_id=oficina.id).all()
            inscritos_info = []
            for inscricao in inscritos:
                usuario = Usuario.query.get(inscricao.usuario_id)
                if usuario:
                    inscritos_info.append({
                        'id': usuario.id,
                        'nome': usuario.nome,
                        'cpf': usuario.cpf,
                        'email': usuario.email,
                        'formacao': usuario.formacao
                    })

            oficinas_com_inscritos.append({
                'id': oficina.id,
                'titulo': oficina.titulo,
                'descricao': oficina.descricao,
                'ministrante': oficina.ministrante,
                'vagas': oficina.vagas,
                'carga_horaria': oficina.carga_horaria,
                'dias': dias_formatados,
                'horarios': [(dia.horario_inicio, dia.horario_fim) for dia in dias],
                'inscritos': inscritos_info
            })

        return render_template('dashboard_admin.html', usuario=current_user, oficinas=oficinas_com_inscritos, permitir_checkin_global=permitir_checkin_global)

    return redirect(url_for('routes.dashboard_participante'))



# ===========================
# GESTÃO DE OFICINAS - ADMIN
# ===========================

@routes.route('/criar_oficina', methods=['GET', 'POST'])
@login_required
def criar_oficina():
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))

    estados = obter_estados()  # Obtém estados para exibição

    if request.method == 'POST':
        print("📌 [DEBUG] Recebendo dados do formulário...")

        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        ministrante = request.form.get('ministrante')
        vagas = request.form.get('vagas')
        carga_horaria = request.form.get('carga_horaria')
        estado = request.form.get('estado')
        cidade = request.form.get('cidade')

        print(f"📌 [DEBUG] Estado: {estado}")
        print(f"📌 [DEBUG] Cidade: {cidade}")

        if not estado or not cidade:
            print("❌ [ERRO] Estado ou cidade não foram recebidos corretamente!")
            flash("Erro: Estado e cidade são obrigatórios!", "danger")
            return redirect(url_for('criar_oficina'))

        # Captura múltiplas datas, horários e palavras-chave
        datas = request.form.getlist('data[]')
        horarios_inicio = request.form.getlist('horario_inicio[]')
        horarios_fim = request.form.getlist('horario_fim[]')
        palavras_chave_manha = request.form.getlist('palavra_chave_manha[]')
        palavras_chave_tarde = request.form.getlist('palavra_chave_tarde[]')

        print(f"📌 [DEBUG] Datas: {datas}")
        print(f"📌 [DEBUG] Horários de início: {horarios_inicio}")
        print(f"📌 [DEBUG] Horários de fim: {horarios_fim}")
        print(f"📌 [DEBUG] Palavras-chave manhã: {palavras_chave_manha}")
        print(f"📌 [DEBUG] Palavras-chave tarde: {palavras_chave_tarde}")

        if not datas or not horarios_inicio or not horarios_fim:
            print("❌ [ERRO] Datas e horários não foram recebidos corretamente!")
            flash('Você deve informar pelo menos uma data e horário!', 'danger')
            return redirect(url_for('criar_oficina'))

        # Criar nova oficina
        nova_oficina = Oficina(
            titulo=titulo,
            descricao=descricao,
            ministrante=ministrante,
            vagas=int(vagas),
            carga_horaria=carga_horaria,
            estado=estado,
            cidade=cidade,
            qr_code=None
        )

        print("✅ [DEBUG] Oficina criada, salvando no banco de dados...")
        db.session.add(nova_oficina)
        db.session.commit()
        print("✅ [DEBUG] Oficina salva com sucesso!")

        # Gerar o QR Code e atualizar o campo
        qr_code_path = gerar_qr_code(nova_oficina.id)
        nova_oficina.qr_code = qr_code_path
        db.session.commit()

        # Adicionar cada data como um dia diferente da oficina
        for i in range(len(datas)):
            novo_dia = OficinaDia(
                oficina_id=nova_oficina.id,
                data=datetime.strptime(datas[i], "%Y-%m-%d").date(),
                horario_inicio=horarios_inicio[i],
                horario_fim=horarios_fim[i],
                palavra_chave_manha=palavras_chave_manha[i],
                palavra_chave_tarde=palavras_chave_tarde[i],
            )
            db.session.add(novo_dia)

        db.session.commit()
        print("✅ [DEBUG] Datas e horários adicionados!")
        
        flash('Oficina criada com sucesso!', 'success')
        return redirect(url_for('routes.dashboard'))

    return render_template(
        'criar_oficina.html',
        estados=estados,
        datas=[],
        horarios_inicio=[],
        horarios_fim=[],
        palavras_chave_manha=[],
        palavras_chave_tarde=[]
    )

def gerar_qr_code(oficina_id):
    # Caminho onde os QR Codes serão salvos
    pasta_qrcodes = os.path.join("static", "qrcodes")
    os.makedirs(pasta_qrcodes, exist_ok=True)  # Cria a pasta se não existir

    # Caminho completo para o arquivo QR Code
    qr_code_path = os.path.join(pasta_qrcodes, f"checkin_{oficina_id}.png")

    # Conteúdo do QR Code
    qr_data = f"/checkin/{oficina_id}"

    # Gerar o QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Salvar o QR Code como imagem
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_code_path)

    return qr_code_path



# Rota para buscar cidades via AJAX
@routes.route('/get_cidades/<estado_sigla>')
def get_cidades(estado_sigla):
    cidades = obter_cidades(estado_sigla)
    print(f"📌 Estado recebido: {estado_sigla}, Cidades encontradas: {cidades}")  # Depuração
    return jsonify(cidades)


@routes.route('/editar_oficina/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def editar_oficina(oficina_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))

    estados = obter_estados()
    oficina = Oficina.query.get_or_404(oficina_id)

    if request.method == 'POST':
        oficina.titulo = request.form['titulo']
        oficina.descricao = request.form['descricao']
        oficina.ministrante = request.form['ministrante']
        oficina.vagas = int(request.form.get('vagas'))
        oficina.carga_horaria = request.form['carga_horaria']
        oficina.estado = request.form['estado']
        oficina.cidade = request.form['cidade']

        # Remover datas antigas e adicionar novas
        OficinaDia.query.filter_by(oficina_id=oficina.id).delete()

        datas = request.form.getlist('data[]')
        horarios_inicio = request.form.getlist('horario_inicio[]')
        horarios_fim = request.form.getlist('horario_fim[]')
        palavras_chave_manha = request.form.getlist('palavra_chave_manha[]')
        palavras_chave_tarde = request.form.getlist('palavra_chave_tarde[]')

        for i in range(len(datas)):
            if datas[i] and horarios_inicio[i] and horarios_fim[i]:
                try:
                    # Converte a data do formato dd/mm/yyyy para um objeto datetime.date
                    data_formatada = datetime.strptime(datas[i], "%Y-%m-%d").date()
                except ValueError:
                    # Gera uma exceção caso o formato da data não seja válido
                    raise ValueError(f"Data inválida: {datas[i]}. O formato esperado é dd/mm/yyyy.")

            novo_dia = OficinaDia(
                oficina_id=oficina.id,
                data=data_formatada,  # Usa a data formatada
                horario_inicio=horarios_inicio[i],
                horario_fim=horarios_fim[i],
                palavra_chave_manha=palavras_chave_manha[i],
                palavra_chave_tarde=palavras_chave_tarde[i],
            )
            db.session.add(novo_dia)

        db.session.commit()
        flash('Oficina editada com sucesso!', 'success')
        return redirect(url_for('routes.dashboard'))

    # Preparar dados para edição
    datas = [dia.data.strftime('%Y-%m-%d') for dia in oficina.dias]
    horarios_inicio = [dia.horario_inicio for dia in oficina.dias]
    horarios_fim = [dia.horario_fim for dia in oficina.dias]
    palavras_chave_manha = [dia.palavra_chave_manha for dia in oficina.dias]
    palavras_chave_tarde = [dia.palavra_chave_tarde for dia in oficina.dias]

    return render_template(
        'editar_oficina.html',
        oficina=oficina,
        estados=estados,
        datas=datas,
        horarios_inicio=horarios_inicio,
        horarios_fim=horarios_fim,
        palavras_chave_manha=palavras_chave_manha,
        palavras_chave_tarde=palavras_chave_tarde
    )



@routes.route('/excluir_oficina/<int:oficina_id>', methods=['POST'])
@login_required
def excluir_oficina(oficina_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))

    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash('Oficina não encontrada!', 'danger')
        return redirect(url_for('routes.dashboard'))

    try:
        print(f"📌 [DEBUG] Excluindo oficina ID: {oficina_id}")

        # Excluir todos os check-ins relacionados à oficina
        db.session.query(Checkin).filter_by(oficina_id=oficina.id).delete()
        db.session.commit()
        print(f"✅ [DEBUG] Check-ins removidos.")

        # Excluir todas as inscrições associadas à oficina
        db.session.query(Inscricao).filter_by(oficina_id=oficina.id).delete()
        db.session.commit()
        print(f"✅ [DEBUG] Inscrições removidas.")

        # Excluir todos os registros de datas da oficina
        db.session.query(OficinaDia).filter_by(oficina_id=oficina.id).delete()
        db.session.commit()
        print(f"✅ [DEBUG] Dias da oficina removidos.")

        # Excluir a oficina
        db.session.delete(oficina)
        db.session.commit()
        print(f"✅ [DEBUG] Oficina removida com sucesso!")

        flash('Oficina excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"❌ [ERRO] Erro ao excluir oficina {oficina_id}: {str(e)}")
        flash(f'Erro ao excluir oficina: {str(e)}', 'danger')

    return redirect(url_for('routes.dashboard'))

# ===========================
# INSCRIÇÃO EM OFICINAS - PARTICIPANTE
# ===========================
from flask import jsonify

@routes.route('/inscrever/<int:oficina_id>', methods=['POST'])
@login_required
def inscrever(oficina_id):
    if current_user.tipo != 'participante':
        flash('Apenas participantes podem se inscrever.', 'danger')
        return redirect(url_for('routes.dashboard_participante'))

    oficina = Oficina.query.get(oficina_id)

    if not oficina:
        flash('Oficina não encontrada!', 'danger')
        return redirect(url_for('routes.dashboard_participante'))

    if oficina.vagas <= 0:
        flash('Esta oficina está lotada!', 'danger')
        return redirect(url_for('routes.dashboard_participante'))

    # Verifica se o usuário já está inscrito
    if Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first():
        flash('Você já está inscrito nesta oficina!', 'warning')
        return redirect(url_for('routes.dashboard_participante'))

    oficina.vagas -= 1
    inscricao = Inscricao(usuario_id=current_user.id, oficina_id=oficina.id)
    db.session.add(inscricao)
    db.session.commit()

    # 📝 Gerar PDF do comprovante
    pdf_path = gerar_comprovante_pdf(current_user, oficina)

    # 🔄 Retorna um JSON com o link do PDF para ser baixado pelo JavaScript
    return jsonify({'success': True, 'pdf_url': url_for('routes.baixar_comprovante', oficina_id=oficina.id)})




    
@routes.route('/remover_inscricao/<int:oficina_id>', methods=['POST'])
@login_required
def remover_inscricao(oficina_id):
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina_id).first()
    
    if not inscricao:
        flash('Você não está inscrito nesta oficina!', 'warning')
        return redirect(url_for('routes.dashboard'))

    oficina = Oficina.query.get(oficina_id)
    if oficina:
        oficina.vagas += 1  # Libera a vaga ao cancelar inscrição

    db.session.delete(inscricao)
    db.session.commit()

    flash('Inscrição removida com sucesso!', 'success')
    return redirect(url_for('routes.dashboard'))

@routes.route('/dashboard_participante')
@login_required
def dashboard_participante():
    if current_user.tipo != 'participante':
        return redirect(url_for('routes.dashboard'))

    # 🔹 Buscar todas as oficinas
    oficinas = Oficina.query.all()

    # 🔹 Buscar a configuração do check-in global no banco de dados
    configuracao = Configuracao.query.first()
    permitir_checkin_global = configuracao.permitir_checkin_global if configuracao else False

    # 🔹 Coletar IDs das oficinas em que o usuário está inscrito
    inscricoes_ids = [inscricao.oficina_id for inscricao in current_user.inscricoes]

    oficinas_inscrito = []
    oficinas_nao_inscrito = []

    for oficina in oficinas:
        dias = OficinaDia.query.filter_by(oficina_id=oficina.id).all()

        oficina_formatada = {
            'id': oficina.id,
            'titulo': oficina.titulo,
            'descricao': oficina.descricao,
            'ministrante': oficina.ministrante,
            'vagas': oficina.vagas,
            'carga_horaria': oficina.carga_horaria,
            'dias': [dia.data.strftime('%d/%m/%Y') for dia in dias],
            'horarios': [(dia.horario_inicio, dia.horario_fim) for dia in dias]
        }

        # 🔹 Separar oficinas em que o usuário está inscrito e as outras
        if oficina.id in inscricoes_ids:
            oficinas_inscrito.append(oficina_formatada)
        else:
            oficinas_nao_inscrito.append(oficina_formatada)

    # 🔹 Juntar as listas, colocando as oficinas inscritas primeiro
    oficinas_ordenadas = oficinas_inscrito + oficinas_nao_inscrito

    return render_template(
        'dashboard_participante.html', 
        usuario=current_user, 
        oficinas=oficinas_ordenadas, 
        permitir_checkin_global=permitir_checkin_global
    )

def gerar_comprovante_pdf(usuario, oficina):
    # Definir nome do arquivo
    pdf_filename = f"comprovante_{usuario.id}_{oficina.id}.pdf"
    pdf_path = os.path.join("static/comprovantes", pdf_filename)

    # Criar diretório caso não exista
    os.makedirs("static/comprovantes", exist_ok=True)

    # Criar o PDF
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Definir fonte e título
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.HexColor("#023E8A"))  # Cor azul escuro
    c.drawString(200, height - 80, "Comprovante de Inscrição")

    # Linha separadora
    c.setStrokeColor(colors.HexColor("#00A8CC"))  # Cor azul claro
    c.setLineWidth(2)
    c.line(50, height - 90, 550, height - 90)

    # Dados do usuário e oficina
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    
    # Define a posição inicial do texto
    y_position = height - 120  

    dados = [
        f"Nome: {usuario.nome}",
        f"CPF: {usuario.cpf}",
        f"E-mail: {usuario.email}",
        f"Oficina: {oficina.titulo}",
        f"Ministrante: {oficina.ministrante}",
    ]

    for dado in dados:
        c.drawString(50, y_position, dado)
        y_position -= 20

    # Adicionar datas
    for dia in oficina.dias:
        c.drawString(50, y_position, f"Data: {dia}")
        y_position -= 20

    # Assinatura do Coordenador
    c.line(50, y_position - 30, 250, y_position - 30)
    c.drawString(50, y_position - 45, "Assinatura do Coordenador")

    # Finaliza e salva o PDF
    c.save()

    # Retorna o caminho do arquivo
    return pdf_path

@routes.route('/baixar_comprovante/<int:oficina_id>')
@login_required
def baixar_comprovante(oficina_id):
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash('Oficina não encontrada!', 'danger')
        return redirect(url_for('routes.dashboard_participante'))

    pdf_path = gerar_comprovante_pdf(current_user, oficina)
    return send_file(pdf_path, as_attachment=True)

# Função para gerar o PDF da lista de inscritos
def gerar_pdf_inscritos_pdf(oficina, pdf_path):
    c = canvas.Canvas(pdf_path, pagesize=letter)
    
    # 🔹 Título principal
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#023E8A"))  # Azul escuro
    c.drawString(180, 750, f"Lista de Inscritos - {oficina.titulo}")

    c.setStrokeColor(colors.black)
    c.line(50, 740, 550, 740)  # Linha separadora

    # 🔹 Informações básicas da oficina
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    c.drawString(50, 720, f"Ministrante: {oficina.ministrante}")

    # 🔹 Seção de Datas e Horários
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#023E8A"))
    c.drawString(50, 700, "Datas e Horários:")

    y_position = 680  # Posição inicial
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.black)

    for dia in oficina.dias:
        data_formatada = dia.data.strftime('%d/%m/%Y')
        horario_inicio = dia.horario_inicio.strftime('%H:%M') if isinstance(dia.horario_inicio, datetime) else dia.horario_inicio
        horario_fim = dia.horario_fim.strftime('%H:%M') if isinstance(dia.horario_fim, datetime) else dia.horario_fim
        
        c.drawString(50, y_position, f"📅 {data_formatada}  |  ⏰ {horario_inicio} às {horario_fim}")
        y_position -= 20  # Move para a próxima linha
    
    c.line(50, y_position - 5, 550, y_position - 5)  # Linha separadora

    # 🔹 Lista de Inscritos em Tabela
    y_position -= 30
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#023E8A"))
    c.drawString(50, y_position, "Lista de Inscritos:")

    y_position -= 20
    c.setFillColor(colors.black)

    # Criando tabela
    table_data = [["Nome", "CPF", "E-mail"]]
    for inscricao in oficina.inscritos:
        table_data.append([inscricao.usuario.nome, inscricao.usuario.cpf, inscricao.usuario.email])

    table = Table(table_data, colWidths=[200, 120, 200])
    
    # Estilizando a tabela
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    
    table.setStyle(style)

    # Desenhando a tabela no PDF
    table.wrapOn(c, 50, y_position)
    table.drawOn(c, 50, y_position - 100)

    # 🔹 Assinatura do Coordenador
    y_position -= (len(oficina.inscritos) * 20) + 130
    c.line(50, y_position, 250, y_position)  # Linha para assinatura
    c.setFont("Helvetica", 11)
    c.drawString(50, y_position - 15, "Assinatura do Coordenador")

    c.save()
    
@routes.route('/gerar_pdf_inscritos/<int:oficina_id>', methods=['GET'])
@login_required
def gerar_pdf_inscritos(oficina_id):
    # Buscar a oficina no banco de dados
    oficina = Oficina.query.get(oficina_id)

    if not oficina:
        flash("Oficina não encontrada!", "danger")
        return redirect(url_for('routes.dashboard'))

    # Criar diretório se não existir
    os.makedirs("static/comprovantes", exist_ok=True)

    # Definir o caminho do PDF
    pdf_filename = f"inscritos_{oficina.id}.pdf"
    pdf_path = os.path.join("static/comprovantes", pdf_filename)

    # Gerar o PDF
    gerar_pdf_inscritos_pdf(oficina, pdf_path)

    # Retornar o PDF para download
    return send_file(pdf_path, as_attachment=True)

def gerar_lista_frequencia_pdf(oficina, pdf_path):
    c = canvas.Canvas(pdf_path, pagesize=letter)
    
    # Configuração da fonte e título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(180, 750, f"Lista de Frequência - {oficina.titulo}")

    c.setFont("Helvetica", 12)
    c.drawString(50, 720, f"Ministrante: {oficina.ministrante}")

    # Adicionando o título para a seção de datas e horários
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 700, "Datas e Horários:")

    y_position = 680
    c.setFont("Helvetica", 11)
    for dia in oficina.dias:
        data_formatada = dia.data.strftime('%d/%m/%Y')
        horario_inicio = dia.horario_inicio.strftime('%H:%M') if isinstance(dia.horario_inicio, datetime) else dia.horario_inicio
        horario_fim = dia.horario_fim.strftime('%H:%M') if isinstance(dia.horario_fim, datetime) else dia.horario_fim

        c.drawString(50, y_position, f"{data_formatada} - {horario_inicio} às {horario_fim}")
        y_position -= 20

    # Criando a tabela da lista de presença
    y_position -= 20
    table_data = [["Nome Completo", "Assinatura"]]

    for inscricao in oficina.inscritos:
        table_data.append([inscricao.usuario.nome, ""])

    # Criando e formatando a tabela
    table = Table(table_data, colWidths=[300, 200])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))

    # Definindo a posição da tabela
    table.wrapOn(c, 50, y_position)
    table.drawOn(c, 50, y_position - (len(table_data) * 20))

    # Espaço para a assinatura do coordenador
    c.drawString(50, y_position - (len(table_data) * 20) - 40, "__________________________")
    c.drawString(50, y_position - (len(table_data) * 20) - 55, "Assinatura do Coordenador")

    c.save()

@routes.route('/gerar_lista_frequencia/<int:oficina_id>')
@login_required
def gerar_lista_frequencia(oficina_id):
    oficina = Oficina.query.get(oficina_id)

    if not oficina:
        flash('Oficina não encontrada!', 'danger')
        return redirect(url_for('routes.dashboard'))

    pdf_filename = f"lista_frequencia_{oficina.id}.pdf"
    pdf_path = os.path.join("static/comprovantes", pdf_filename)

    gerar_lista_frequencia_pdf(oficina, pdf_path)

    return send_file(pdf_path, as_attachment=True)

def gerar_certificados_pdf(oficina, inscritos, pdf_path):
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    
    # Caminho da logo (alterar conforme necessidade)
    #logo_path = "static/logo.png"  # Caminho do logotipo
    fundo_path = "static/Certificado IAFAP.png"  # Caminho do template de fundo

    for inscrito in inscritos:
        # Inserir plano de fundo
        try:
            fundo = ImageReader(fundo_path)
            c.drawImage(fundo, 0, 0, width=A4[1], height=A4[0])  # Ajusta ao tamanho da página
        except:
            print("⚠️ Fundo do certificado não encontrado. Continuando sem fundo personalizado.")


        # Nome do Participante
        c.setFont("AlexBrush", 35)
        c.setFillColor(colors.black)
        c.drawCentredString(420, 310, f"{inscrito.usuario.nome}")

        # Informações da Oficina
        c.setFont("Helvetica", 16)
        texto_oficina = f"participou da oficina {oficina.titulo}, ministrada por {oficina.ministrante},"
        c.drawCentredString(420, 270, texto_oficina)

        texto_carga_horaria = f"com carga horária de {oficina.carga_horaria} horas, realizada nos dias:"
        c.drawCentredString(420, 240, texto_carga_horaria)

        # Adicionando as datas formatadas
        # Montar a string de datas formatadas com vírgulas e "e"
        if len(oficina.dias) > 1:
            datas_formatadas = ", ".join([dia.data.strftime('%d/%m/%Y') for dia in oficina.dias[:-1]]) + \
                            " e " + oficina.dias[-1].data.strftime('%d/%m/%Y') + "."  # Última data
        else:
            datas_formatadas = oficina.dias[0].data.strftime('%d/%m/%Y')

        # Desenhar a string no PDF
        c.setFont("Helvetica", 16)
        c.drawCentredString(420, 210, datas_formatadas)



        # Rodapé com QR Code (Opcional)
        #try:
        #    import qrcode
        #    qr_code_data = f"https://seusistema.com/verificar_certificado/{inscrito.usuario.id}/{oficina.id}"
        #    qr = qrcode.make(qr_code_data)
        #   qr_path = f"static/qrcodes/qrcode_{inscrito.usuario.id}_{oficina.id}.png"
        #   qr.save(qr_path)
        #   c.drawImage(qr_path, 700, 50, width=80, height=80)
        #except:
        #    print("⚠️ Biblioteca QR Code não instalada. QR Code não será incluído.")

        # Nova página para o próximo certificado
        c.showPage()

    c.save()

@routes.route('/gerar_certificados/<int:oficina_id>', methods=['GET'])
@login_required
def gerar_certificados(oficina_id):
    if current_user.tipo != 'admin':
        flash("Apenas administradores podem gerar certificados.", "danger")
        return redirect(url_for('routes.dashboard'))

    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash("Oficina não encontrada!", "danger")
        return redirect(url_for('routes.dashboard'))

    inscritos = oficina.inscritos
    if not inscritos:
        flash("Não há inscritos nesta oficina para gerar certificados!", "warning")
        return redirect(url_for('routes.dashboard'))

    # Caminho do PDF
    pdf_path = f"static/certificados/certificados_oficina_{oficina.id}.pdf"

    # Criar o diretório se não existir
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Gerar o PDF
    gerar_certificados_pdf(oficina, inscritos, pdf_path)

    flash("Certificados gerados com sucesso!", "success")
    return send_file(pdf_path, as_attachment=True)

@routes.route('/checkin/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def checkin(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)
    dias = OficinaDia.query.filter_by(oficina_id=oficina_id).order_by(OficinaDia.data).all()

    if request.method == 'POST':
        dia_id = request.form.get('dia_id')
        palavra_chave_manha = request.form.get('palavra_chave_manha')
        palavra_chave_tarde = request.form.get('palavra_chave_tarde')

        # Valida o dia selecionado
        dia = OficinaDia.query.get(dia_id)
        if not dia:
            flash("Dia selecionado não é válido!", "danger")
            return redirect(url_for('checkin', oficina_id=oficina_id))

        # Valida palavra-chave da manhã
        if dia.palavra_chave_manha and dia.palavra_chave_manha != palavra_chave_manha:
            flash("Palavra-chave da manhã está incorreta!", "danger")
            return redirect(url_for('checkin', oficina_id=oficina_id))

        # Valida palavra-chave da tarde, se fornecida
        if palavra_chave_tarde and dia.palavra_chave_tarde and dia.palavra_chave_tarde != palavra_chave_tarde:
            flash("Palavra-chave da tarde está incorreta!", "danger")
            return redirect(url_for('checkin', oficina_id=oficina_id))

        # Registra o check-in
        checkin = Checkin(
            usuario_id=current_user.id,
            oficina_id=oficina.id,
            palavra_chave=palavra_chave_manha if palavra_chave_manha else palavra_chave_tarde
        )
        db.session.add(checkin)
        db.session.commit()

        flash("Check-in realizado com sucesso!", "success")
        return redirect(url_for('routes.dashboard'))

    return render_template('checkin.html', oficina=oficina, dias=dias)




@routes.route('/oficina/<int:oficina_id>/checkins', methods=['GET'])
@login_required
def lista_checkins(oficina_id):
    if current_user.tipo != 'admin':
        flash("Acesso negado!", "danger")
        return redirect(url_for('routes.dashboard'))

    # Obtém a oficina
    oficina = Oficina.query.get_or_404(oficina_id)

    # Lista de check-ins associados à oficina
    checkins = Checkin.query.filter_by(oficina_id=oficina_id).all()

    # Detalhes dos usuários que realizaram check-in
    usuarios_checkin = [
        {
            'nome': checkin.usuario.nome,
            'cpf': checkin.usuario.cpf,
            'email': checkin.usuario.email,
            'data_hora': checkin.data_hora.strftime('%d/%m/%Y %H:%M:%S')
        }
        for checkin in checkins
    ]

    return render_template(
        'lista_checkins.html',
        oficina=oficina,
        usuarios_checkin=usuarios_checkin
    )


@routes.route('/gerar_pdf_checkins/<int:oficina_id>', methods=['GET'])
@login_required
def gerar_pdf_checkins(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)
    checkins = Checkin.query.filter_by(oficina_id=oficina_id).all()
    dias = OficinaDia.query.filter_by(oficina_id=oficina_id).all()

    # Caminho do PDF
    pdf_path = f"static/checkins_oficina_{oficina.id}.pdf"

    # Configurações de estilo
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        name="Header",
        parent=styles["Heading1"],
        alignment=1,  # Centralizado
        fontSize=14,
        spaceAfter=12,
    )
    normal_style = styles["Normal"]

    # Gerar o PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elementos = []

    # Cabeçalho da oficina
    elementos.append(Paragraph(f"Lista de Check-ins - {oficina.titulo}", header_style))
    elementos.append(Spacer(1, 12))  # Espaço entre o título e o resto
    elementos.append(Paragraph(f"<b>Ministrante:</b> {oficina.ministrante}", normal_style))
    elementos.append(Paragraph(f"<b>Local:</b> {oficina.cidade}, {oficina.estado}", normal_style))
    
    # Adiciona as datas da oficina
    if dias:
        elementos.append(Paragraph("<b>Datas:</b>", normal_style))
        for dia in dias:
            data_formatada = dia.data.strftime('%d/%m/%Y')
            elementos.append(Paragraph(f" - {data_formatada} ({dia.horario_inicio} às {dia.horario_fim})", normal_style))
    else:
        elementos.append(Paragraph("<b>Datas:</b> Nenhuma data registrada", normal_style))
    
    elementos.append(Spacer(1, 20))  # Espaço antes da tabela

    # Tabela de check-ins
    data = [["Nome", "CPF", "E-mail", "Data e Hora do Check-in"]]
    for checkin in checkins:
        data.append([
            checkin.usuario.nome,
            checkin.usuario.cpf,
            checkin.usuario.email,
            checkin.data_hora.strftime("%d/%m/%Y %H:%M"),
        ])

    tabela = Table(data, colWidths=[150, 100, 200, 150])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elementos.append(tabela)

    # Construir o PDF
    doc.build(elementos)

    return send_file(pdf_path, as_attachment=True)



@routes.route('/gerar_pdf/<int:oficina_id>')
def gerar_pdf(oficina_id):
    # Buscar a oficina no banco de dados
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash("Oficina não encontrada!", "danger")
        return redirect(url_for('dashboard_admin'))

    # Caminho do arquivo PDF
    pdf_path = os.path.join("static", "pdfs")
    os.makedirs(pdf_path, exist_ok=True)
    pdf_file = os.path.join(pdf_path, f"oficina_{oficina_id}.pdf")

    # Criando o PDF em formato A4 paisagem
    c = canvas.Canvas(pdf_file, pagesize=landscape(A4))
    width, height = landscape(A4)  # Dimensões do A4 em paisagem

    # Adicionar a logo no topo (se existir)
    logo_path = os.path.join("static", "logom.png")
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        c.drawImage(logo, width / 2 - 100, height - 100, width=200, height=80, preserveAspectRatio=True, mask='auto')

    # Adicionar uma linha separadora
    c.setLineWidth(2)
    c.line(50, height - 120, width - 50, height - 120)

    # Título da oficina (destacado como placa)
    c.setFont("Helvetica-Bold", 36)
    c.setFillColorRGB(0, 0, 0.7)  # Azul escuro para destaque
    c.drawCentredString(width / 2, height - 180, oficina.titulo.upper())


    # Ministrante (com destaque)
    c.setFont("Helvetica-Bold", 22)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(width / 2, height - 230, f"Ministrante: {oficina.ministrante}")

    # Adicionar uma linha separadora
    c.setLineWidth(1)
    c.line(50, height - 250, width - 50, height - 250)

    # Título da seção de datas
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.drawCentredString(width / 2, height - 280, "Datas e Horários")


    # Lista de Datas da Oficina
    c.setFont("Helvetica", 16)
    c.setFillColorRGB(0, 0, 0)
    y_pos = height - 300
    for dia in oficina.dias:
        c.drawCentredString(width / 2, y_pos, f"{dia.data.strftime('%d/%m/%Y')} - {dia.horario_inicio} às {dia.horario_fim}")
        y_pos -= 30

   # Adicionar a imagem "jornada2025.png" no rodapé
    jornada_path = os.path.join("static", "jornada2025.png")
    if os.path.exists(jornada_path):
        jornada = ImageReader(jornada_path)

    # Centraliza a imagem na largura da página
    x_centered = (width - 600) / 2  # Calcula a posição X para centralizar
    c.drawImage(jornada, x_centered, 20, width=600, height=240, preserveAspectRatio=True, mask='auto')



    # Salvar PDF
    c.save()

    return send_file(pdf_file, as_attachment=True, download_name=f"oficina_{oficina_id}.pdf")

@routes.route('/esqueci_senha_cpf', methods=['GET', 'POST'])
def esqueci_senha_cpf():
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        usuario = Usuario.query.filter_by(cpf=cpf).first()
        
        if usuario:
            # Armazena o ID do usuário na sessão
            session['reset_user_id'] = usuario.id
            return redirect(url_for('routes.reset_senha_cpf'))
        else:
            flash('CPF não encontrado!', 'danger')
            return redirect(url_for('routes.esqueci_senha_cpf'))

    
    return render_template('esqueci_senha_cpf.html')

def enviar_email_reset(email, link_reset):
    msg = Message("Redefinição de Senha",
                  recipients=[email],
                  sender="naoresponda@seudominio.com")
    msg.body = f"""Olá,

Para redefinir sua senha, clique no link abaixo ou cole em seu navegador:

{link_reset}

Se você não solicitou, ignore este e-mail.
"""
    mail.send(msg)

@routes.route('/reset_senha_cpf', methods=['GET', 'POST'])
def reset_senha_cpf():
    # Pega o ID do usuário armazenado na sessão
    user_id = session.get('reset_user_id')
    if not user_id:
        flash('Nenhum usuário selecionado para redefinição!', 'danger')
        return redirect(url_for('routes.esqueci_senha_cpf'))


    usuario = Usuario.query.get(user_id)
    if not usuario:
        flash('Usuário não encontrado no banco de dados!', 'danger')
        return redirect(url_for('routes.esqueci_senha_cpf'))


    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        if not nova_senha or nova_senha != confirmar_senha:
            flash('As senhas não coincidem ou são inválidas.', 'danger')
            return redirect(url_for('routes.reset_senha_cpf'))

        # Atualiza a senha (com hash)
        usuario.senha = generate_password_hash(nova_senha)
        db.session.commit()
        
        # Remove da sessão para evitar reutilizações
        session.pop('reset_user_id', None)
        
        flash('Senha redefinida com sucesso! Faça login novamente.', 'success')
        return redirect(url_for('routes.login'))


    return render_template('reset_senha_cpf.html', usuario=usuario)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"xlsx"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def arquivo_permitido(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@routes.route("/importar_oficinas", methods=["POST"])
@login_required
def importar_oficinas():
    if "arquivo" not in request.files:
        flash("Nenhum arquivo enviado!", "danger")
        return redirect(url_for("routes.dashboard"))

    arquivo = request.files["arquivo"]
    
    if arquivo.filename == "":
        flash("Nenhum arquivo selecionado.", "danger")
        return redirect(url_for("routes.dashboard"))

    if arquivo and arquivo_permitido(arquivo.filename):
        filename = secure_filename(arquivo.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        arquivo.save(filepath)

        try:
            print("📌 [DEBUG] Lendo o arquivo Excel...")
            df = pd.read_excel(filepath)

            # 🔥 REMOVE ESPAÇOS E TABULAÇÕES DOS NOMES DAS COLUNAS
            df.columns = df.columns.str.strip()

            print("📌 [DEBUG] Colunas encontradas:", df.columns.tolist())

            # Validando se todas as colunas necessárias estão no arquivo
            colunas_obrigatorias = [
                "titulo", "descricao", "ministrante", "vagas", "carga_horaria",
                "estado", "cidade", "datas", "horarios_inicio", "horarios_fim",
                "palavras_chave_manha", "palavras_chave_tarde"
            ]
            if not all(col in df.columns for col in colunas_obrigatorias):
                flash(f"Erro: O arquivo deve conter as colunas: {', '.join(colunas_obrigatorias)}", "danger")
                return redirect(url_for("routes.dashboard"))

            oficinas_criadas = 0

            for index, row in df.iterrows():
                print(f"\n📌 [DEBUG] Processando linha {index+1}...")

                nova_oficina = Oficina(
                    titulo=row["titulo"],
                    descricao=row["descricao"],
                    ministrante=row["ministrante"],
                    vagas=int(row["vagas"]),
                    carga_horaria=str(row["carga_horaria"]),
                    estado=row["estado"].upper(),  
                    cidade=row["cidade"]
                )
                db.session.add(nova_oficina)
                db.session.commit()
                print(f"✅ [DEBUG] Oficina '{nova_oficina.titulo}' cadastrada com sucesso!")

                # Processando datas e horários
                datas = row["datas"].split(",")
                horarios_inicio = row["horarios_inicio"].split(",")
                horarios_fim = row["horarios_fim"].split(",")
                palavras_chave_manha = row["palavras_chave_manha"].split(",") if isinstance(row["palavras_chave_manha"], str) else []
                palavras_chave_tarde = row["palavras_chave_tarde"].split(",") if isinstance(row["palavras_chave_tarde"], str) else []

                for i in range(len(datas)):
                    try:
                    # Convertendo para o formato correto "DD/MM/YYYY"
                        data_formatada = datetime.strptime(datas[i].strip(), "%d/%m/%Y").date()
                        print(f"📌 [DEBUG] Adicionando data: {data_formatada}, {horarios_inicio[i]} - {horarios_fim[i]}")
                    except ValueError as e:
                        print(f"❌ [ERRO] Data inválida na linha {index+1}: {datas[i]} - {str(e)}")
                        continue  

                novo_dia = OficinaDia(
                    oficina_id=nova_oficina.id,
                    data=data_formatada,
                    horario_inicio=horarios_inicio[i].strip(),
                    horario_fim=horarios_fim[i].strip(),
                    palavra_chave_manha=palavras_chave_manha[i].strip() if i < len(palavras_chave_manha) else None,
                    palavra_chave_tarde=palavras_chave_tarde[i].strip() if i < len(palavras_chave_tarde) else None
                )
                db.session.add(novo_dia)

                db.session.commit()
                oficinas_criadas += 1

            flash(f"{oficinas_criadas} oficinas importadas com sucesso!", "success")
            print(f"✅ [DEBUG] {oficinas_criadas} oficinas foram importadas com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ [ERRO] Erro ao processar o arquivo: {str(e)}")
            flash(f"Erro ao processar o arquivo: {str(e)}", "danger")

        os.remove(filepath)

    else:
        flash("Formato de arquivo inválido. Envie um arquivo Excel (.xlsx)", "danger")

    return redirect(url_for("routes.dashboard"))



@routes.route("/excluir_todas_oficinas", methods=["POST"])
@login_required
def excluir_todas_oficinas():
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for("routes.dashboard"))

    try:
        # 📌 Debug: Verificar quantidade de oficinas antes da exclusão
        oficinas = Oficina.query.all()
        if not oficinas:
            flash("Não há oficinas para excluir.", "warning")
            return redirect(url_for("routes.dashboard"))

        print(f"📌 [DEBUG] Encontradas {len(oficinas)} oficinas para exclusão.")

        # 🔹 Exclui os QR Codes antes de deletar as oficinas
        qr_code_folder = os.path.join("static", "qrcodes")
        for oficina in oficinas:
            if oficina.qr_code:
                qr_code_path = os.path.join(qr_code_folder, f"checkin_{oficina.id}.png")
                if os.path.exists(qr_code_path):
                    os.remove(qr_code_path)
                    print(f"✅ [DEBUG] QR Code removido: {qr_code_path}")

        # 🔹 Exclui todas as inscrições antes de deletar oficinas
        num_inscricoes = db.session.query(Inscricao).delete()
        print(f"✅ [DEBUG] {num_inscricoes} inscrições excluídas.")

        # 🔹 Exclui todos os check-ins antes de deletar oficinas
        num_checkins = db.session.query(Checkin).delete()
        print(f"✅ [DEBUG] {num_checkins} check-ins excluídos.")

        # 🔹 Exclui todos os registros de datas da oficina
        num_dias = db.session.query(OficinaDia).delete()
        print(f"✅ [DEBUG] {num_dias} registros de dias excluídos.")

        # 🔹 Exclui todas as oficinas
        num_oficinas = db.session.query(Oficina).delete()
        print(f"✅ [DEBUG] {num_oficinas} oficinas excluídas.")

        # 🔄 Confirma as alterações no banco
        db.session.commit()

        flash(f"{num_oficinas} oficinas e todos os dados relacionados foram excluídos com sucesso!", "success")

    except Exception as e:
        db.session.rollback()
        print(f"❌ [ERRO] Erro ao excluir oficinas: {str(e)}")
        flash(f"Erro ao excluir oficinas: {str(e)}", "danger")

    return redirect(url_for("routes.dashboard"))

from werkzeug.security import generate_password_hash

from werkzeug.security import generate_password_hash

@routes.route("/importar_usuarios", methods=["POST"])
def importar_usuarios():
    if "arquivo" not in request.files:
        flash("Nenhum arquivo enviado!", "danger")
        return redirect(url_for("routes.dashboard"))

    arquivo = request.files["arquivo"]
    
    if arquivo.filename == "":
        flash("Nenhum arquivo selecionado.", "danger")
        return redirect(url_for("routes.dashboard"))

    if arquivo and arquivo_permitido(arquivo.filename):
        filename = secure_filename(arquivo.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        arquivo.save(filepath)

        try:
            print("📌 [DEBUG] Lendo o arquivo Excel...")
            df = pd.read_excel(filepath, dtype={"cpf": str})  # 🔹 Converte CPF para string
            print(f"📌 [DEBUG] Colunas encontradas: {df.columns.tolist()}")

            # Verificando se as colunas necessárias estão presentes
            colunas_obrigatorias = ["nome", "cpf", "email", "senha", "formacao", "tipo"]
            if not all(col in df.columns for col in colunas_obrigatorias):
                flash("Erro: O arquivo deve conter as colunas: " + ", ".join(colunas_obrigatorias), "danger")
                return redirect(url_for("routes.dashboard"))

            # Inserindo no banco de dados
            total_importados = 0
            for _, row in df.iterrows():
                cpf_str = str(row["cpf"]).strip()  # 🔹 Garante que o CPF seja tratado como string

                # Verificando se o e-mail já existe
                usuario_existente = Usuario.query.filter_by(email=row["email"]).first()
                if usuario_existente:
                    print(f"⚠️ [DEBUG] Usuário com e-mail {row['email']} já existe. Pulando...")
                    continue  # Ignorar duplicados

                # Verificando se o CPF já existe
                usuario_existente = Usuario.query.filter_by(cpf=cpf_str).first()
                if usuario_existente:
                    print(f"⚠️ [DEBUG] Usuário com CPF {cpf_str} já existe. Pulando...")
                    continue  # Ignorar duplicados

                # Hash da senha antes de salvar
                senha_hash = generate_password_hash(str(row["senha"]))

                # Criando usuário
                novo_usuario = Usuario(
                    nome=row["nome"],
                    cpf=cpf_str,  # 🔹 Garante que o CPF seja armazenado como string
                    email=row["email"],
                    senha=senha_hash,
                    formacao=row["formacao"],
                    tipo=row["tipo"]
                )
                db.session.add(novo_usuario)
                total_importados += 1

                print(f"✅ [DEBUG] Usuário '{row['nome']}' cadastrado com sucesso!")

            db.session.commit()
            flash(f"{total_importados} usuários importados com sucesso!", "success")

        except Exception as e:
            db.session.rollback()
            print(f"❌ [ERRO] Erro ao importar usuários: {str(e)}")
            flash(f"Erro ao processar o arquivo: {str(e)}", "danger")

        os.remove(filepath)

    else:
        flash("Formato de arquivo inválido. Envie um arquivo Excel (.xlsx)", "danger")

    return redirect(url_for("routes.dashboard"))

@routes.route("/toggle_checkin_global", methods=["POST"])
@login_required
def toggle_checkin_global():
    if current_user.tipo != "admin":
        flash("Acesso negado!", "danger")
        return redirect(url_for("routes.dashboard"))

    # Buscar ou criar a configuração
    config = Configuracao.query.first()
    if not config:
        config = Configuracao(permitir_checkin_global=False)
        db.session.add(config)

    # Alternar o estado do check-in global
    config.permitir_checkin_global = not config.permitir_checkin_global
    db.session.commit()

    status = "ativado" if config.permitir_checkin_global else "desativado"
    flash(f"Check-in global {status} com sucesso!", "success")
    
    return redirect(url_for("routes.dashboard"))
