import os
import uuid
import csv
from flask import Response
from datetime import datetime
import logging
import pandas as pd
import qrcode
import requests
from flask import abort
from sqlalchemy.exc import IntegrityError
from flask import send_from_directory
from models import Ministrante
from models import Cliente
from flask import (Flask, Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, send_file, session)
from flask_login import login_user, logout_user, login_required, current_user
from flask_login import LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import RespostaFormulario, RespostaCampo


# Extensões e modelos (utilize sempre o mesmo ponto de importação para o db)
from extensions import db, login_manager
from models import (Usuario, Oficina, Inscricao, OficinaDia, Checkin,
                    Configuracao, Feedback, Ministrante, RelatorioOficina, MaterialOficina)
from utils import obter_estados, obter_cidades, gerar_qr_code, gerar_qr_code_inscricao, gerar_comprovante_pdf   # Funções auxiliares
from reportlab.lib.units import inch
from reportlab.platypus import Image

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from models import LinkCadastro
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from models import Formulario, CampoFormulario
from extensions import db
from flask_login import login_required, current_user


# ReportLab para PDFs
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


# Registrar a fonte personalizada
pdfmetrics.registerFont(TTFont("AlexBrush", "AlexBrush-Regular.ttf"))

# Configurações da aplicação e Blueprint
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
ALLOWED_EXTENSIONS = {"xlsx"}

# Inicialize o LoginManager com o app e defina a rota de login.
login_manager.init_app(app)
login_manager.login_view = 'routes.login'  # Essa é a rota que será usada para login

routes = Blueprint("routes", __name__)

def register_routes(app):
    app.register_blueprint(routes)


# ===========================
#        ROTAS GERAIS
# ===========================

@routes.route('/')
def home():
    return render_template('index.html')


# ===========================
#    CADASTRO DE PARTICIPANTE
# ===========================
@routes.route('/cadastro_participante', methods=['GET', 'POST'])
def cadastro_participante():
    alert = None
    token = request.args.get('token')  # Pega o token da URL se existir
    cliente_id = None

    # Se houver um token, verifica se é válido
    if token:
        link = LinkCadastro.query.filter_by(token=token).first()
        if not link:
            flash("Erro: Link de cadastro inválido ou expirado!", "danger")
            return redirect(url_for('routes.cadastro_participante'))
        cliente_id = link.cliente_id  # Associa ao Cliente

    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        senha = request.form.get('senha')
        formacao = request.form.get('formacao')
        estados = request.form.getlist('estados[]')
        cidades = request.form.getlist('cidades[]')
        estados_str = ','.join(estados) if estados else ''
        cidades_str = ','.join(cidades) if cidades else ''

        print(f"📌 Recebido: Nome={nome}, CPF={cpf}, Email={email}, Formação={formacao}, Estados={estados_str}, Cidades={cidades_str}, Cliente ID={cliente_id}")

        # Verifica se o e-mail já existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash('Erro: Este e-mail já está cadastrado!', 'danger')
            return redirect(url_for('routes.cadastro_participante', token=token) if token else url_for('routes.cadastro_participante'))

        # Verifica se o CPF já existe
        usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
        if usuario_existente:
            alert = {"category": "danger", "message": "CPF já está sendo usado por outro usuário!"}
        elif not senha:
            alert = {"category": "danger", "message": "A senha é obrigatória!"}
        else:
            novo_usuario = Usuario(
                nome=nome,
                cpf=cpf,
                email=email,
                senha=generate_password_hash(senha),
                formacao=formacao,
                tipo='participante',
                estados=estados_str,
                cidades=cidades_str,
                cliente_id=cliente_id  # Associa ao Cliente se veio por link
            )
            try:
                db.session.add(novo_usuario)
                db.session.commit()
                flash("Cadastro realizado com sucesso!", "success")
                return redirect(url_for('routes.login'))
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao cadastrar usuário: {e}")
                alert = {"category": "danger", "message": "Erro ao cadastrar. Tente novamente!"}

    return render_template('cadastro_participante.html', alert=alert, token=token)


# ===========================
#      EDITAR PARTICIPANTE
# ===========================

@routes.route('/editar_participante', methods=['GET', 'POST'])
@login_required
def editar_participante():
    # Verifica se o usuário logado é do tipo participante
    if current_user.tipo != 'participante':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
    
    if request.method == 'POST':
        # Captura os dados enviados pelo formulário de edição
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        formacao = request.form.get('formacao')
        # Captura os arrays dos locais (estados e cidades)
        estados = request.form.getlist('estados[]')
        cidades = request.form.getlist('cidades[]')
        # Atualiza os dados do usuário
        current_user.nome = nome
        current_user.cpf = cpf
        current_user.email = email
        current_user.formacao = formacao
        # Armazena os locais como strings separadas por vírgula
        current_user.estados = ','.join(estados) if estados else ''
        current_user.cidades = ','.join(cidades) if cidades else ''
        
        # Se o participante informar uma nova senha, atualiza-a
        nova_senha = request.form.get('senha')
        if nova_senha:
            current_user.senha = generate_password_hash(nova_senha)
        
        try:
            db.session.commit()
            flash("Perfil atualizado com sucesso!", "success")
            return redirect(url_for('routes.dashboard_participante'))
        except Exception as e:
            db.session.rollback()
            flash("Erro ao atualizar o perfil: " + str(e), "danger")
    
    # Renderiza o template passando o usuário logado (current_user)
    return render_template('editar_participante.html', usuario=current_user)


# ===========================
#      GESTÃO DE USUÁRIOS
# ===========================
@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')
    if user_type == 'ministrante':
        return Ministrante.query.get(int(user_id))
    elif user_type in ['admin', 'participante']:
        return Usuario.query.get(int(user_id))
    elif user_type == 'cliente':
        from models import Cliente
        return Cliente.query.get(int(user_id))
    # Fallback: tenta buscar em Usuario e Ministrante
    user = Usuario.query.get(int(user_id))
    if user:
        return user
    return Ministrante.query.get(int(user_id))



@routes.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        print(f"Tentativa de login para o email: {email}, senha: {senha}")

        # Busca o usuário no banco de dados
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            print(f"Usuário encontrado na tabela Usuario: {usuario.email}, tipo: {getattr(usuario, 'tipo', 'N/A')}, senha salva: {usuario.senha}")
        else:
            print("Não encontrado na tabela Usuario, buscando em Ministrante...")
            usuario = Ministrante.query.filter_by(email=email).first()
            if usuario:
                print(f"Usuário encontrado na tabela Ministrante: {usuario.email}, senha salva: {usuario.senha}")
            else:
                print("Não encontrado na tabela Ministrante, buscando em Cliente...")
                usuario = Cliente.query.filter_by(email=email).first()
                if usuario:
                    if not usuario.is_active():
                        flash('Sua conta está desativada. Contate o administrador.', 'danger')
                        return render_template('login.html')
                    if check_password_hash(usuario.senha, senha):
                        session['user_type'] = 'cliente'
                        login_user(usuario)
                        flash('Login realizado com sucesso!', 'success')
                        return redirect(url_for('routes.dashboard_cliente'))
                    flash('E-mail ou senha incorretos!', 'danger')
                    print(f"Usuário encontrado na tabela Cliente: {usuario.email}, senha salva: {usuario.senha}")
                else:
                    print("Usuário não encontrado em nenhuma tabela.")

        # Verifica a senha
        if usuario:
            print(f"Comparando senha digitada ({senha}) com senha salva ({usuario.senha})")

            # Verifica se a senha está em texto puro ou se é um hash
            if usuario.senha.startswith("scrypt:") or usuario.senha.startswith("pbkdf2:") or usuario.senha.startswith("sha256$"):
                senha_correta = check_password_hash(usuario.senha, senha)
            else:
                senha_correta = usuario.senha == senha

            if senha_correta:
                print("Senha verificada com sucesso!")
                
                session['user_type'] = (
                    'ministrante' if isinstance(usuario, Ministrante) else
                    'cliente' if isinstance(usuario, Cliente) else
                    usuario.tipo if hasattr(usuario, 'tipo') else 'usuario'
                )

                login_user(usuario)
                flash('Login realizado com sucesso!', 'success')

                # Redirecionamento conforme o tipo de usuário
                redirecionamentos = {
                    'admin': 'routes.dashboard',
                    'cliente': 'routes.dashboard_cliente',
                    'participante': 'routes.dashboard_participante',
                    'ministrante': 'routes.dashboard_ministrante'
                }
                destino = redirecionamentos.get(session.get('user_type'), 'routes.dashboard_ministrante')
                print(f"Redirecionando para {destino}")
                return redirect(url_for(destino))
            else:
                print("Senha incorreta.")
        else:
            print("Usuário não encontrado.")

        flash('E-mail ou senha incorretos!', 'danger')

    return render_template('login.html')


@routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'info')
    return redirect(url_for('routes.home'))


# ===========================
#  DASHBOARD ADMIN & PARTICIPANTE
# ===========================
@routes.route('/dashboard')
@login_required
def dashboard():
    from sqlalchemy import func

    # Obtem filtros
    estado_filter = request.args.get('estado', '').strip()
    cidade_filter = request.args.get('cidade', '').strip()

    # Check-ins via QR
    checkins_via_qr = Checkin.query.filter_by(palavra_chave='QR-AUTO').all()

    # Lista de participantes (se quiser gerenciar)
    participantes = Usuario.query.filter_by(tipo='participante').all()
    
    inscricoes = Inscricao.query.all()
    
    msg_relatorio = None  # Adiciona um valor padrão

    # Verifica o tipo de usuário
    is_admin = current_user.tipo == 'admin'
    is_cliente = current_user.tipo == 'cliente'
    
    # Se for admin, busca também os clientes
    clientes = []
    if is_admin:
        clientes = Cliente.query.all()

    # ========== 1) Dados gerais ==========
    if is_admin:
        total_oficinas = Oficina.query.count()
        total_vagas = db.session.query(func.sum(Oficina.vagas)).scalar() or 0
        total_inscricoes = Inscricao.query.count()
    else:  # Cliente vê apenas suas oficinas
        total_oficinas = Oficina.query.filter_by(cliente_id=current_user.id).count()
        total_vagas = db.session.query(func.sum(Oficina.vagas)).filter(Oficina.cliente_id == current_user.id).scalar() or 0
        total_inscricoes = Inscricao.query.join(Oficina).filter(Oficina.cliente_id == current_user.id).count()

    percentual_adesao = (total_inscricoes / total_vagas) * 100 if total_vagas > 0 else 0

    # ========== 2) Estatísticas por oficina ==========
    oficinas_query = Oficina.query.filter_by(cliente_id=current_user.id) if is_cliente else Oficina.query
    oficinas = oficinas_query.all()

    lista_oficinas_info = []
    for of in oficinas:
        num_inscritos = Inscricao.query.filter_by(oficina_id=of.id).count()
        perc_ocupacao = (num_inscritos / of.vagas) * 100 if of.vagas > 0 else 0

        lista_oficinas_info.append({
            'titulo': of.titulo,
            'vagas': of.vagas,
            'inscritos': num_inscritos,
            'ocupacao': perc_ocupacao
        })

    # ========== 3) Monta a string do relatório (somente UMA vez) ==========
    msg_relatorio = (
        "📊 *Relatório do Sistema*\n\n"
        f"✅ *Total de Oficinas:* {total_oficinas}\n"
        f"✅ *Vagas Ofertadas:* {total_vagas}\n"
        f"✅ *Vagas Preenchidas:* {total_inscricoes}\n"
        f"✅ *% de Adesão:* {percentual_adesao:.2f}%\n\n"
        "----------------------------------------\n"
        "📌 *DADOS POR OFICINA:*\n"
    )

    for info in lista_oficinas_info:
        msg_relatorio += (
            f"\n🎓 *Oficina:* {info['titulo']}\n"
            f"🔹 *Vagas:* {info['vagas']}\n"
            f"🔹 *Inscritos:* {info['inscritos']}\n"
            f"🔹 *Ocupação:* {info['ocupacao']:.2f}%\n"
        )

    # ========== 4) Mais lógica para dashboard (filtros, etc.) ==========
    query = oficinas_query
    if estado_filter:
        query = query.filter(Oficina.estado == estado_filter)
    if cidade_filter:
        query = query.filter(Oficina.cidade == cidade_filter)
    oficinas_filtradas = query.all()

    oficinas_com_inscritos = []
    for oficina in oficinas_filtradas:
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
            'ministrante': oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A',
            'vagas': oficina.vagas,
            'carga_horaria': oficina.carga_horaria,
            'dias': dias_formatados,
            'inscritos': inscritos_info
        })

    # Busca ministrantes, relatorios, config...
    ministrantes = Ministrante.query.all()
    relatorios = RelatorioOficina.query.order_by(RelatorioOficina.enviado_em.desc()).all()
    configuracao = Configuracao.query.first()
    permitir_checkin_global = configuracao.permitir_checkin_global if configuracao else False
    habilitar_feedback = configuracao.habilitar_feedback if configuracao else False
    habilitar_certificado_individual = configuracao.habilitar_certificado_individual if configuracao else False

    # ========== 5) Renderiza ==========
    return render_template(
        'dashboard_admin.html' if is_admin else 'dashboard_cliente.html',
        participantes=participantes,
        usuario=current_user,
        oficinas=oficinas_com_inscritos,
        ministrantes=ministrantes,
        relatorios=relatorios,
        permitir_checkin_global=permitir_checkin_global,
        habilitar_feedback=habilitar_feedback,
        estado_filter=estado_filter,
        cidade_filter=cidade_filter,
        checkins_via_qr=checkins_via_qr,
        total_oficinas=total_oficinas,
        total_vagas=total_vagas,
        total_inscricoes=total_inscricoes,
        percentual_adesao=percentual_adesao,
        oficinas_estatisticas=lista_oficinas_info,
        msg_relatorio=msg_relatorio,
        inscricoes=inscricoes,
        habilitar_certificado_individual=habilitar_certificado_individual,
        clientes=clientes
    )

@routes.route('/dashboard_participante')
@login_required
def dashboard_participante():
    if current_user.tipo != 'participante':
        return redirect(url_for('routes.dashboard'))

    print(f"🔍 Participante autenticado: {current_user.email}, Cliente ID: {current_user.cliente_id}")

    if current_user.cliente_id:
        oficinas = Oficina.query.filter(
            (Oficina.cliente_id == current_user.cliente_id) | (Oficina.cliente_id == None)
        ).all()
    else:
        # Participantes sem cliente associado veem apenas oficinas do Admin
        oficinas = Oficina.query.filter(Oficina.cliente_id == None).all()

    # Configurações globais
    configuracao = Configuracao.query.first()
    permitir_checkin_global = configuracao.permitir_checkin_global if configuracao else False
    habilitar_feedback = configuracao.habilitar_feedback if configuracao else False
    habilitar_certificado_individual = configuracao.habilitar_certificado_individual if configuracao else False

    inscricoes_ids = [inscricao.oficina_id for inscricao in current_user.inscricoes]
    oficinas_inscrito = []
    oficinas_nao_inscrito = []

    for oficina in oficinas:
        dias = OficinaDia.query.filter_by(oficina_id=oficina.id).all()
        oficina_formatada = {
            'id': oficina.id,
            'titulo': oficina.titulo,
            'descricao': oficina.descricao,
            'ministrante': oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A',
            'vagas': oficina.vagas,
            'carga_horaria': oficina.carga_horaria,
            'dias': [dia.data.strftime('%d/%m/%Y') for dia in dias],
            'horarios': [(dia.horario_inicio, dia.horario_fim) for dia in dias]
        }
        if oficina.id in inscricoes_ids:
            oficinas_inscrito.append(oficina_formatada)
        else:
            oficinas_nao_inscrito.append(oficina_formatada)

    oficinas_ordenadas = oficinas_inscrito + oficinas_nao_inscrito

    return render_template('dashboard_participante.html', 
                           usuario=current_user, 
                           oficinas=oficinas_ordenadas, 
                           permitir_checkin_global=permitir_checkin_global,
                           habilitar_feedback=habilitar_feedback,
                           habilitar_certificado_individual=habilitar_certificado_individual)



# ===========================
#    GESTÃO DE OFICINAS - ADMIN
# ===========================
@routes.route('/criar_oficina', methods=['GET', 'POST'])
@login_required
def criar_oficina():
    if current_user.tipo not in ['admin', 'cliente']:  # Apenas Admin e Cliente podem criar oficinas
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))

    estados = obter_estados()
    todos_ministrantes = Ministrante.query.all()

    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        ministrante_id = request.form.get('ministrante_id')
        vagas = request.form.get('vagas')
        carga_horaria = request.form.get('carga_horaria')
        estado = request.form.get('estado')
        cidade = request.form.get('cidade')

        if not estado or not cidade:
            flash("Erro: Estado e cidade são obrigatórios!", "danger")
            return redirect(url_for('routes.criar_oficina'))

        nova_oficina = Oficina(
            titulo=titulo,
            descricao=descricao,
            ministrante_id=ministrante_id,
            vagas=int(vagas),
            carga_horaria=carga_horaria,
            estado=estado,
            cidade=cidade,
            cliente_id=current_user.id if current_user.tipo == 'cliente' else None  # Cliente cria apenas suas oficinas
        )

        db.session.add(nova_oficina)
        db.session.commit()

        flash('Oficina criada com sucesso!', 'success')
        return redirect(url_for('routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'routes.dashboard'))

    return render_template(
        'criar_oficina.html',
        estados=estados,
        ministrantes=todos_ministrantes
    )


@routes.route('/get_cidades/<estado_sigla>')
def get_cidades(estado_sigla):
    cidades = obter_cidades(estado_sigla)
    print(f"📌 Estado recebido: {estado_sigla}, Cidades encontradas: {cidades}")
    return jsonify(cidades)


@routes.route('/editar_oficina/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def editar_oficina(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)

    # Cliente só pode editar oficinas que ele criou
    if current_user.tipo == 'cliente' and oficina.cliente_id != current_user.id:
        flash('Você não tem permissão para editar esta oficina.', 'danger')
        return redirect(url_for('routes.dashboard_cliente'))

    estados = obter_estados()
    ministrantes = Ministrante.query.all()

    if request.method == 'POST':
        oficina.titulo = request.form.get('titulo')
        oficina.descricao = request.form.get('descricao')
        oficina.ministrante_id = request.form.get('ministrante_id')
        oficina.vagas = int(request.form.get('vagas'))
        oficina.carga_horaria = request.form.get('carga_horaria')
        oficina.estado = request.form.get('estado')
        oficina.cidade = request.form.get('cidade')

        db.session.commit()
        flash('Oficina editada com sucesso!', 'success')

        if current_user.tipo == 'cliente':
            return redirect(url_for('routes.dashboard_cliente'))
        return redirect(url_for('routes.dashboard'))

    return render_template('editar_oficina.html', oficina=oficina, estados=estados, ministrantes=ministrantes)


@routes.route('/excluir_oficina/<int:oficina_id>', methods=['POST'])
@login_required
def excluir_oficina(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)

    # 🚨 Cliente só pode excluir oficinas que ele criou
    if current_user.tipo == 'cliente' and oficina.cliente_id != current_user.id:
        flash('Você não tem permissão para excluir esta oficina.', 'danger')
        return redirect(url_for('routes.dashboard_cliente'))

    try:
        print(f"📌 [DEBUG] Excluindo oficina ID: {oficina_id}")

        # 1️⃣ **Excluir check-ins relacionados à oficina**
        db.session.query(Checkin).filter_by(oficina_id=oficina.id).delete()
        print("✅ [DEBUG] Check-ins removidos.")

        # 2️⃣ **Excluir inscrições associadas à oficina**
        db.session.query(Inscricao).filter_by(oficina_id=oficina.id).delete()
        print("✅ [DEBUG] Inscrições removidas.")

        # 3️⃣ **Excluir registros de datas da oficina (OficinaDia)**
        db.session.query(OficinaDia).filter_by(oficina_id=oficina.id).delete()
        print("✅ [DEBUG] Dias da oficina removidos.")

        # 4️⃣ **Excluir materiais da oficina**
        db.session.query(MaterialOficina).filter_by(oficina_id=oficina.id).delete()
        print("✅ [DEBUG] Materiais da oficina removidos.")

        # 5️⃣ **Excluir relatórios associados à oficina**
        db.session.query(RelatorioOficina).filter_by(oficina_id=oficina.id).delete()
        print("✅ [DEBUG] Relatórios da oficina removidos.")

        # 6️⃣ **Excluir a própria oficina**
        db.session.delete(oficina)
        db.session.commit()
        print("✅ [DEBUG] Oficina removida com sucesso!")
        flash('Oficina excluída com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        print(f"❌ [ERRO] Erro ao excluir oficina {oficina_id}: {str(e)}")
        flash(f'Erro ao excluir oficina: {str(e)}', 'danger')

    return redirect(url_for('routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'routes.dashboard'))


# ===========================
# INSCRIÇÃO EM OFICINAS - PARTICIPANTE
# ===========================
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

    # Evita duplicidade
    if Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first():
        flash('Você já está inscrito nesta oficina!', 'warning')
        return redirect(url_for('routes.dashboard_participante'))

    # Decrementa vagas e cria a Inscricao
    oficina.vagas -= 1
    inscricao = Inscricao(usuario_id=current_user.id, oficina_id=oficina.id)
    inscricao.cliente_id = current_user.cliente_id
    db.session.add(inscricao)
    db.session.commit()

    # Gera PDF de comprovante (com QR Code embutido)
    pdf_path = gerar_comprovante_pdf(current_user, oficina, inscricao)
    
    # Retorna via JSON (pode ficar do mesmo jeito ou redirecionar)
    return jsonify({'success': True, 'pdf_url': url_for('routes.baixar_comprovante', oficina_id=oficina.id)})

@routes.route('/remover_inscricao/<int:oficina_id>', methods=['POST'])
@login_required
def remover_inscricao(oficina_id):
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina_id).first()
    if not inscricao:
        flash('Você não está inscrito nesta oficina!', 'warning')
        return redirect(url_for('routes.dashboard_participante'))

    oficina = Oficina.query.get(oficina_id)
    if oficina:
        oficina.vagas += 1

    db.session.delete(inscricao)
    db.session.commit()
    flash('Inscrição removida com sucesso!', 'success')
    return redirect(url_for('routes.dashboard_participante'))


# ===========================
#   COMPROVANTE DE INSCRIÇÃO (PDF)
# ===========================
@routes.route('/leitor_checkin', methods=['GET'])
@login_required
def leitor_checkin():
    # Se quiser que somente admin/staff faça check-in, verifique current_user.tipo
    # if current_user.tipo not in ('admin', 'staff'):
    #     flash("Acesso negado!", "danger")
    #     return redirect(url_for('routes.dashboard'))

    # 1. Obtém o token enviado pelo QR Code
    token = request.args.get('token')
    if not token:
        flash("Token não fornecido ou inválido.", "danger")
        return redirect(url_for('routes.dashboard'))

    # 2. Busca a inscrição correspondente
    inscricao = Inscricao.query.filter_by(qr_code_token=token).first()
    if not inscricao:
        flash("Inscrição não encontrada para este token.", "danger")
        return redirect(url_for('routes.dashboard'))

    # 3. Verifica se o check-in já foi feito anteriormente
    checkin_existente = Checkin.query.filter_by(
        usuario_id=inscricao.usuario_id, 
        oficina_id=inscricao.oficina_id
    ).first()
    if checkin_existente:
        flash("Check-in já foi realizado!", "warning")
        return redirect(url_for('routes.dashboard'))

    # 4. Registra o novo check-in
    novo_checkin = Checkin(
        usuario_id=inscricao.usuario_id,
        oficina_id=inscricao.oficina_id,
        palavra_chave="QR-AUTO"  # Se quiser indicar que foi via QR
    )
    db.session.add(novo_checkin)
    db.session.commit()

    flash("Check-in realizado com sucesso!", "success")
    # 5. Redireciona ao dashboard (admin ou participante, conforme sua lógica)
    return redirect(url_for('routes.dashboard'))

@routes.route('/baixar_comprovante/<int:oficina_id>')
@login_required
def baixar_comprovante(oficina_id):
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash('Oficina não encontrada!', 'danger')
        return redirect(url_for('routes.dashboard_participante'))

    # Busca a inscrição do usuário logado nessa oficina
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first()
    if not inscricao:
        flash('Você não está inscrito nesta oficina.', 'danger')
        return redirect(url_for('routes.dashboard_participante'))

    # Agora chamamos a função com o parâmetro adicional "inscricao"
    pdf_path = gerar_comprovante_pdf(current_user, oficina, inscricao)
    return send_file(pdf_path, as_attachment=True)


# ===========================
# GERAÇÃO DE PDFs (Inscritos, Lista de Frequência, Certificados, Check-ins, Oficina)
# ===========================

def gerar_lista_frequencia_pdf(oficina, pdf_path):
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter

    # Configurações do documento
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []

    # Título
    elements.append(Paragraph(f"Lista de Frequência - {oficina.titulo}", styles['Title']))
    elements.append(Spacer(1, 12))

    # Informações da oficina
    ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A'
    elements.append(Paragraph(f"<b>Ministrante:</b> {ministrante_nome}", styles['Normal']))
    elements.append(Paragraph(f"<b>Local:</b> {oficina.cidade}, {oficina.estado}", styles['Normal']))

    # Datas e horários
    if oficina.dias:
        elements.append(Paragraph("<b>Datas e Horários:</b>", styles['Normal']))
        for dia in oficina.dias:
            data_formatada = dia.data.strftime('%d/%m/%Y')
            horario_inicio = dia.horario_inicio
            horario_fim = dia.horario_fim
            elements.append(Paragraph(f"📅 {data_formatada} | ⏰ {horario_inicio} às {horario_fim}", styles['Normal']))
    else:
        elements.append(Paragraph("<b>Datas:</b> Nenhuma data registrada", styles['Normal']))

    elements.append(Spacer(1, 20))

    # Tabela de frequência
    table_data = [["Nome Completo", "Assinatura"]]
    for inscricao in oficina.inscritos:
        table_data.append([
            Paragraph(inscricao.usuario.nome, styles['Normal']),
            "",  # Espaço para assinatura
        ])

    # Criar a tabela
    table = Table(table_data, colWidths=[300, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Assinatura
    elements.append(Paragraph("Assinatura do Coordenador", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Gerar o PDF
    doc.build(elements)
    
    
@routes.route('/gerar_pdf_inscritos/<int:oficina_id>', methods=['GET'])
@login_required
def gerar_pdf_inscritos_pdf(oficina_id):
    # Busca a oficina no banco de dados
    oficina = Oficina.query.get_or_404(oficina_id)
    
    # Define o caminho onde o PDF será salvo
    pdf_filename = f"inscritos_oficina_{oficina.id}.pdf"
    pdf_path = os.path.join("static/comprovantes", pdf_filename)
    os.makedirs("static/comprovantes", exist_ok=True)

    # Configurações do documento
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []

    # Título
    elements.append(Paragraph(f"Lista de Inscritos - {oficina.titulo}", styles['Title']))
    elements.append(Spacer(1, 12))

    # Informações da oficina
    ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A'
    elements.append(Paragraph(f"<b>Ministrante:</b> {ministrante_nome}", styles['Normal']))
    elements.append(Paragraph(f"<b>Local:</b> {oficina.cidade}, {oficina.estado}", styles['Normal']))

    # Datas e horários
    if oficina.dias:
        elements.append(Paragraph("<b>Datas e Horários:</b>", styles['Normal']))
        for dia in oficina.dias:
            data_formatada = dia.data.strftime('%d/%m/%Y')
            horario_inicio = dia.horario_inicio
            horario_fim = dia.horario_fim
            elements.append(Paragraph(f"📅 {data_formatada} | ⏰ {horario_inicio} às {horario_fim}", styles['Normal']))
    else:
        elements.append(Paragraph("<b>Datas:</b> Nenhuma data registrada", styles['Normal']))

    elements.append(Spacer(1, 20))

    # Tabela de inscritos
    table_data = [["Nome", "CPF", "E-mail"]]
    for inscricao in oficina.inscritos:
        table_data.append([
            Paragraph(inscricao.usuario.nome, styles['Normal']),
            Paragraph(inscricao.usuario.cpf, styles['Normal']),
            Paragraph(inscricao.usuario.email, styles['Normal']),
        ])

    # Criar a tabela
    table = Table(table_data, colWidths=[200, 120, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Assinatura
    elements.append(Paragraph("Assinatura do Coordenador", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Gerar o PDF
    doc.build(elements)

    # Retorna o arquivo PDF gerado
    return send_file(pdf_path, as_attachment=True)
    
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

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

def wrap_text(text, font, font_size, max_width, canvas):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if canvas.stringWidth(test_line, font, font_size) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def gerar_certificados_pdf(oficina, inscritos, pdf_path):
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    fundo_path = "static/Certificado IAFAP.png"
    for inscrito in inscritos:
        try:
            fundo = ImageReader(fundo_path)
            c.drawImage(fundo, 0, 0, width=A4[1], height=A4[0])
        except Exception as e:
            print("⚠️ Fundo do certificado não encontrado:", e)
        
        # Texto da oficina com quebra de linha manual
        c.setFont("Helvetica", 16)
        texto_oficina = (f"{inscrito.usuario.nome}, portador do {inscrito.usuario.cpf}, participou da oficina de tema "
                          f"{oficina.titulo}, com carga horária total de {oficina.carga_horaria} horas, Este certificado é "
                          f"concedido como reconhecimento pela dedicação e participação no evento realizado na cidade "
                          f"{oficina.cidade} nos dias:")
        max_width = 600  # largura máxima permitida para o texto
        lines = wrap_text(texto_oficina, "Helvetica", 16, max_width, c)
        y = 340
        for line in lines:
            c.drawCentredString(420, y, line)
            y -= 25  # espaçamento entre linhas
        
        # Datas da oficina
        if len(oficina.dias) > 1:
            datas_formatadas = ", ".join([dia.data.strftime('%d/%m/%Y') for dia in oficina.dias[:-1]]) + \
                                " e " + oficina.dias[-1].data.strftime('%d/%m/%Y') + "."
        else:
            datas_formatadas = oficina.dias[0].data.strftime('%d/%m/%Y')
        c.drawCentredString(420, y, datas_formatadas)
        
        # Adiciona a assinatura como imagem
        try:
            signature_path = "static/signature.png"  # Caminho da imagem da assinatura
            signature_width = 360  # Largura da assinatura em pontos
            signature_height = 90  # Altura da assinatura em pontos
            # Centraliza horizontalmente (considerando que a página em paisagem tem 840 pontos de largura, ex: A4[1])
            x_signature = 420 - (signature_width / 2)
            y_signature = y - 187  # Ajuste vertical; 80 pontos abaixo do último texto (datas)
            c.drawImage(signature_path, x_signature, y_signature,
                        width=signature_width, height=signature_height,
                        preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print("Erro ao adicionar a assinatura:", e)
        
        c.showPage()
    c.save()



    
@routes.route('/gerar_certificados/<int:oficina_id>', methods=['GET'])
@login_required
def gerar_certificados(oficina_id):
    if current_user.tipo not in ['admin', 'cliente']:
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
    pdf_path = f"static/certificados/certificados_oficina_{oficina.id}.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    gerar_certificados_pdf(oficina, inscritos, pdf_path)
    flash("Certificados gerados com sucesso!", "success")
    return send_file(pdf_path, as_attachment=True)

@routes.route('/checkin/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def checkin(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)
    
    if request.method == 'POST':
        palavra_escolhida = request.form.get('palavra_escolhida')
        if not palavra_escolhida:
            flash("Selecione uma opção de check-in.", "danger")
            return redirect(url_for('routes.checkin', oficina_id=oficina_id))
        
        # Verifica se o usuário está inscrito na oficina
        inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first()
        if not inscricao:
            flash("Você não está inscrito nesta oficina!", "danger")
            return redirect(url_for('routes.checkin', oficina_id=oficina_id))
        
        # Se o usuário já errou duas vezes, bloqueia o check-in
        if inscricao.checkin_attempts >= 2:
            flash("Você excedeu o número de tentativas de check-in.", "danger")
            return redirect(url_for('routes.dashboard'))
        
        # Verifica se a alternativa escolhida é a correta
        if palavra_escolhida.strip() != oficina.palavra_correta.strip():
            inscricao.checkin_attempts += 1
            db.session.commit()
            flash("Palavra-chave incorreta!", "danger")
            return redirect(url_for('routes.checkin', oficina_id=oficina_id))
        
        # Se a resposta estiver correta, registra o check-in
        checkin = Checkin(
            usuario_id=current_user.id,
            oficina_id=oficina.id,
            palavra_chave=palavra_escolhida
        )
        db.session.add(checkin)
        db.session.commit()
        flash("Check-in realizado com sucesso!", "success")
        return redirect(url_for('routes.dashboard'))
    
    # Para o GET: extrai as opções configuradas (supondo que foram salvas como uma string separada por vírgulas)
    opcoes = oficina.opcoes_checkin.split(',') if oficina.opcoes_checkin else []
    return render_template('checkin.html', oficina=oficina, opcoes=opcoes)


@routes.route('/oficina/<int:oficina_id>/checkins', methods=['GET'])
@login_required
def lista_checkins(oficina_id):
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Acesso negado!", "danger")
        return redirect(url_for('routes.dashboard'))
    oficina = Oficina.query.get_or_404(oficina_id)
    checkins = Checkin.query.filter_by(oficina_id=oficina_id).all()
    usuarios_checkin = [{
        'nome': checkin.usuario.nome,
        'cpf': checkin.usuario.cpf,
        'email': checkin.usuario.email,
        'data_hora': checkin.data_hora.strftime('%d/%m/%Y %H:%M:%S')
    } for checkin in checkins]
    return render_template('lista_checkins.html', oficina=oficina, usuarios_checkin=usuarios_checkin)

@routes.route('/gerar_pdf_checkins/<int:oficina_id>', methods=['GET'])
@login_required
def gerar_pdf_checkins(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)
    checkins = Checkin.query.filter_by(oficina_id=oficina_id).all()
    dias = OficinaDia.query.filter_by(oficina_id=oficina_id).all()
    pdf_path = f"static/checkins_oficina_{oficina.id}.pdf"
    
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        name="Header",
        parent=styles["Heading1"],
        alignment=1,
        fontSize=14,
        spaceAfter=12,
    )
    normal_style = styles["Normal"]
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elementos = []
    
    # Corrigido: Acessa ministrante via ministrante_obj
    ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A'
    
    elementos.append(Paragraph(f"Lista de Check-ins - {oficina.titulo}", header_style))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(f"<b>Ministrante:</b> {ministrante_nome}", normal_style))  # Linha corrigida
    elementos.append(Paragraph(f"<b>Local:</b> {oficina.cidade}, {oficina.estado}", normal_style))
    
    if dias:
        elementos.append(Paragraph("<b>Datas:</b>", normal_style))
        for dia in dias:
            data_formatada = dia.data.strftime('%d/%m/%Y')
            elementos.append(Paragraph(
                f" - {data_formatada} ({dia.horario_inicio} às {dia.horario_fim})", 
                normal_style
            ))
    else:
        elementos.append(Paragraph("<b>Datas:</b> Nenhuma data registrada", normal_style))
    
    elementos.append(Spacer(1, 20))
    
    # Tabela de check-ins
    data_table = [["Nome", "CPF", "E-mail", "Data e Hora do Check-in"]]
    for checkin in checkins:
        data_table.append([
            checkin.usuario.nome,
            checkin.usuario.cpf,
            checkin.usuario.email,
            checkin.data_hora.strftime("%d/%m/%Y %H:%M"),
        ])
    
    from reportlab.platypus import Table
    tabela = Table(data_table, colWidths=[150, 100, 200, 150])
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
    doc.build(elementos)
    return send_file(pdf_path, as_attachment=True)

@routes.route('/gerar_pdf/<int:oficina_id>')
def gerar_pdf(oficina_id):
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash("Oficina não encontrada!", "danger")
        return redirect(url_for('routes.dashboard'))
    pdf_path = os.path.join("static", "pdfs")
    os.makedirs(pdf_path, exist_ok=True)
    pdf_file = os.path.join(pdf_path, f"oficina_{oficina_id}.pdf")
    c = canvas.Canvas(pdf_file, pagesize=landscape(A4))
    width, height = landscape(A4)
    logo_path = os.path.join("static", "logom.png")
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        c.drawImage(logo, width / 2 - 100, height - 100, width=200, height=80, preserveAspectRatio=True, mask='auto')
    c.setLineWidth(2)
    c.line(50, height - 120, width - 50, height - 120)
    c.setFont("Helvetica-Bold", 36)
    c.setFillColorRGB(0, 0, 0.7)
    c.drawCentredString(width / 2, height - 180, oficina.titulo.upper())
    c.setFont("Helvetica-Bold", 22)
    c.setFillColorRGB(0, 0, 0)
    ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A'
    c.drawCentredString(width / 2, height - 230, f"Ministrante: {ministrante_nome}")
    c.setLineWidth(1)
    c.line(50, height - 250, width - 50, height - 250)
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.drawCentredString(width / 2, height - 280, "Datas e Horários")
    c.setFont("Helvetica", 16)
    c.setFillColorRGB(0, 0, 0)
    y_pos = height - 300
    for dia in oficina.dias:
        c.drawCentredString(width / 2, y_pos, f"{dia.data.strftime('%d/%m/%Y')} - {dia.horario_inicio} às {dia.horario_fim}")
        y_pos -= 30
    jornada_path = os.path.join("static", "jornada2025.png")
    if os.path.exists(jornada_path):
        jornada = ImageReader(jornada_path)
        x_centered = (width - 600) / 2
        c.drawImage(jornada, x_centered, 20, width=600, height=240, preserveAspectRatio=True, mask='auto')
    c.save()
    return send_file(pdf_file, as_attachment=True, download_name=f"oficina_{oficina_id}.pdf")


@routes.route('/gerar_certificado_individual_admin', methods=['POST'])
@login_required
def gerar_certificado_individual_admin():
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Acesso negado!", "danger")
        return redirect(url_for('routes.dashboard'))

    oficina_id = request.form.get('oficina_id')
    usuario_id = request.form.get('usuario_id')
    
    if not oficina_id or not usuario_id:
        flash("Oficina ou participante não informado.", "danger")
        return redirect(url_for('routes.dashboard'))

    # Busca a oficina
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash("Oficina não encontrada!", "danger")
        return redirect(url_for('routes.dashboard'))

    # Verifica se o participante está inscrito na oficina
    inscricao = Inscricao.query.filter_by(oficina_id=oficina_id, usuario_id=usuario_id).first()
    if not inscricao:
        flash("O participante não está inscrito nesta oficina!", "danger")
        return redirect(url_for('routes.dashboard'))

    # Define o caminho do PDF e gera o certificado
    pdf_path = f"static/certificados/certificado_{usuario_id}_{oficina_id}_admin.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Gera o certificado utilizando a função existente; observe que passamos uma lista contendo só essa inscrição
    gerar_certificados_pdf(oficina, [inscricao], pdf_path)

    flash("Certificado individual gerado com sucesso!", "success")
    return send_file(pdf_path, as_attachment=True)


# ===========================
#   RESET DE SENHA VIA CPF
# ===========================
@routes.route('/esqueci_senha_cpf', methods=['GET', 'POST'])
def esqueci_senha_cpf():
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        usuario = Usuario.query.filter_by(cpf=cpf).first()
        if usuario:
            session['reset_user_id'] = usuario.id
            return redirect(url_for('routes.reset_senha_cpf'))
        else:
            flash('CPF não encontrado!', 'danger')
            return redirect(url_for('routes.esqueci_senha_cpf'))
    return render_template('esqueci_senha_cpf.html')

@routes.route('/reset_senha_cpf', methods=['GET', 'POST'])
def reset_senha_cpf():
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
        usuario.senha = generate_password_hash(nova_senha)
        db.session.commit()
        session.pop('reset_user_id', None)
        flash('Senha redefinida com sucesso! Faça login novamente.', 'success')
        return redirect(url_for('routes.login'))
    return render_template('reset_senha_cpf.html', usuario=usuario)


# ===========================
#       IMPORTAÇÃO DE ARQUIVOS
# ===========================
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
            df.columns = df.columns.str.strip()
            print("📌 [DEBUG] Colunas encontradas:", df.columns.tolist())
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
                datas = row["datas"].split(",")
                horarios_inicio = row["horarios_inicio"].split(",")
                horarios_fim = row["horarios_fim"].split(",")
                palavras_chave_manha = row["palavras_chave_manha"].split(",") if isinstance(row["palavras_chave_manha"], str) else []
                palavras_chave_tarde = row["palavras_chave_tarde"].split(",") if isinstance(row["palavras_chave_tarde"], str) else []
                for i in range(len(datas)):
                    try:
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
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado!', 'danger')
        return redirect(url_for("routes.dashboard"))

    try:
        if current_user.tipo == 'admin':
            oficinas = Oficina.query.all()
        else:  # Cliente só pode excluir suas próprias oficinas
            oficinas = Oficina.query.filter_by(cliente_id=current_user.id).all()

        if not oficinas:
            flash("Não há oficinas para excluir.", "warning")
            return redirect(url_for("routes.dashboard_cliente" if current_user.tipo == 'cliente' else "routes.dashboard"))

        for oficina in oficinas:
            db.session.query(Checkin).filter_by(oficina_id=oficina.id).delete()
            db.session.query(Inscricao).filter_by(oficina_id=oficina.id).delete()
            db.session.query(OficinaDia).filter_by(oficina_id=oficina.id).delete()
            db.session.query(MaterialOficina).filter_by(oficina_id=oficina.id).delete()
            db.session.query(RelatorioOficina).filter_by(oficina_id=oficina.id).delete()
            db.session.delete(oficina)

        db.session.commit()
        flash("Oficinas excluídas com sucesso!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir oficinas: {str(e)}", "danger")

    return redirect(url_for("routes.dashboard_cliente" if current_user.tipo == 'cliente' else "routes.dashboard"))


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
            df = pd.read_excel(filepath, dtype={"cpf": str})
            print(f"📌 [DEBUG] Colunas encontradas: {df.columns.tolist()}")
            colunas_obrigatorias = ["nome", "cpf", "email", "senha", "formacao", "tipo"]
            if not all(col in df.columns for col in colunas_obrigatorias):
                flash("Erro: O arquivo deve conter as colunas: " + ", ".join(colunas_obrigatorias), "danger")
                return redirect(url_for("routes.dashboard"))
            total_importados = 0
            for _, row in df.iterrows():
                cpf_str = str(row["cpf"]).strip()
                usuario_existente = Usuario.query.filter_by(email=row["email"]).first()
                if usuario_existente:
                    print(f"⚠️ [DEBUG] Usuário com e-mail {row['email']} já existe. Pulando...")
                    continue
                usuario_existente = Usuario.query.filter_by(cpf=cpf_str).first()
                if usuario_existente:
                    print(f"⚠️ [DEBUG] Usuário com CPF {cpf_str} já existe. Pulando...")
                    continue
                senha_hash = generate_password_hash(str(row["senha"]))
                novo_usuario = Usuario(
                    nome=row["nome"],
                    cpf=cpf_str,
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
    config = Configuracao.query.first()
    if not config:
        config = Configuracao(permitir_checkin_global=False, habilitar_feedback=False)
        db.session.add(config)
    config.permitir_checkin_global = not config.permitir_checkin_global
    db.session.commit()
    status = "ativado" if config.permitir_checkin_global else "desativado"
    print(f"🔍 Check-in Global está {'Ativado' if config.permitir_checkin_global else 'Desativado'}")
    return redirect(url_for("routes.dashboard"))


@routes.route("/toggle_certificado_individual", methods=["POST"])
@login_required
def toggle_certificado_individual():
    if current_user.tipo != "admin":
        flash("Acesso negado!", "danger")
        return redirect(url_for("routes.dashboard"))

    config = Configuracao.query.first()
    if not config:
        # Se não houver registro, cria um
        config = Configuracao(
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False
        )
        db.session.add(config)

    # Inverte o booleano
    config.habilitar_certificado_individual = not config.habilitar_certificado_individual
    db.session.commit()

    status = "ativado" if config.habilitar_certificado_individual else "desativado"
    flash(f"Certificado individual {status} com sucesso!", "success")
    return redirect(url_for("routes.dashboard"))


# ===========================
#         FEEDBACK
# ===========================
@routes.route('/feedback/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def feedback(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)
    if current_user.tipo != 'participante':
        flash('Apenas participantes podem enviar feedback.', 'danger')
        return redirect(url_for('routes.dashboard'))
    if request.method == 'POST':
        try:
            rating = int(request.form.get('rating', 0))
        except ValueError:
            rating = 0
        comentario = request.form.get('comentario', '').strip()
        if rating < 1 or rating > 5:
            flash('A avaliação deve ser entre 1 e 5 estrelas.', 'danger')
            return redirect(url_for('routes.feedback', oficina_id=oficina_id))
        novo_feedback = Feedback(
            usuario_id=current_user.id,
            oficina_id=oficina.id,
            rating=rating,
            comentario=comentario
        )
        db.session.add(novo_feedback)
        db.session.commit()
        flash('Feedback enviado com sucesso!', 'success')
        return redirect(url_for('routes.dashboard_participante'))
    return render_template('feedback.html', oficina=oficina)

@routes.route('/feedback_oficina/<int:oficina_id>')
@login_required
def feedback_oficina(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)  # Primeiro
    if current_user.tipo not in ['admin', 'cliente'] or (current_user.tipo == 'cliente' and oficina.cliente_id != current_user.id and oficina.cliente_id is not None):
        flash('Você não tem permissão para visualizar o feedback desta oficina.', 'danger')
        return redirect(url_for('routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'routes.dashboard'))

    # Cálculo das estatísticas gerais (sem os filtros da query abaixo)
    total_feedbacks_all = Feedback.query.filter_by(oficina_id=oficina_id).all()
    total_count = len(total_feedbacks_all)
    total_avg = (sum(fb.rating for fb in total_feedbacks_all) / total_count) if total_count > 0 else 0

    feedbacks_usuarios = Feedback.query.filter(
        Feedback.oficina_id == oficina_id,
        Feedback.usuario_id.isnot(None)
    ).all()
    count_usuarios = len(feedbacks_usuarios)
    avg_usuarios = (sum(fb.rating for fb in feedbacks_usuarios) / count_usuarios) if count_usuarios > 0 else 0

    feedbacks_ministrantes = Feedback.query.filter(
        Feedback.oficina_id == oficina_id,
        Feedback.ministrante_id.isnot(None)
    ).all()
    count_ministrantes = len(feedbacks_ministrantes)
    avg_ministrantes = (sum(fb.rating for fb in feedbacks_ministrantes) / count_ministrantes) if count_ministrantes > 0 else 0

    # Aplicando filtros (tipo e número de estrelas) para a listagem
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
    
    return render_template('feedback_oficina.html', oficina=oficina, feedbacks=feedbacks,
                           total_count=total_count, total_avg=total_avg,
                           count_ministrantes=count_ministrantes, avg_ministrantes=avg_ministrantes,
                           count_usuarios=count_usuarios, avg_usuarios=avg_usuarios)



def gerar_pdf_feedback(oficina, feedbacks, pdf_path):
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, SimpleDocTemplate
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from datetime import datetime

    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading4'],
        textColor=colors.white
    )

    elements = []
    # Título
    title = Paragraph(f"Feedbacks da Oficina - {oficina.titulo}", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Cria a linha de cabeçalho utilizando Paragraph para melhor formatação
    header = [
        Paragraph("Usuário", heading_style),
        Paragraph("Avaliação", heading_style),
        Paragraph("Comentário", heading_style),
        Paragraph("Data", heading_style)
    ]
    table_data = [header]
    
    # Prepara os dados da tabela (usando Paragraph para células com texto possivelmente longo)
    for fb in feedbacks:
        rating_str = '★' * fb.rating + '☆' * (5 - fb.rating)
        data_str = fb.created_at.strftime('%d/%m/%Y %H:%M')
        nome_autor = fb.usuario.nome if fb.usuario is not None else (
                     fb.ministrante.nome if fb.ministrante is not None else "Desconhecido")
        # Cria um Paragraph para o comentário para permitir quebra de linha
        comentario_paragraph = Paragraph(fb.comentario or "", normal_style)
        row = [
            Paragraph(nome_autor, normal_style),
            Paragraph(rating_str, normal_style),
            comentario_paragraph,
            Paragraph(data_str, normal_style)
        ]
        table_data.append(row)
    
    # Cria o documento em modo paisagem com margens pequenas
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter), leftMargin=36, rightMargin=36)
    available_width = doc.width  # largura disponível após as margens

    # Define as larguras das colunas (porcentagem da largura disponível)
    col_widths = [
        available_width * 0.2,  # Usuário
        available_width * 0.15, # Avaliação
        available_width * 0.45, # Comentário
        available_width * 0.2   # Data
    ]
    
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    footer = Paragraph("Feedbacks gerados em " + datetime.utcnow().strftime('%d/%m/%Y %H:%M'), normal_style)
    elements.append(footer)
    elements.append(PageBreak())
    
    doc.build(elements)


@routes.route('/gerar_pdf_feedback/<int:oficina_id>')
@login_required
def gerar_pdf_feedback_route(oficina_id):
    if current_user.tipo != 'admin' and current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
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


@routes.route("/toggle_feedback", methods=["POST"])
@login_required
def toggle_feedback():
    if current_user.tipo != "admin":
        flash("Acesso negado!", "danger")
        return redirect(url_for("routes.dashboard_participante"))
    config = Configuracao.query.first()
    if not config:
        config = Configuracao(permitir_checkin_global=False, habilitar_feedback=False)
        db.session.add(config)
    config.habilitar_feedback = not config.habilitar_feedback
    db.session.commit()
    flash(f"Feedback global {'ativado' if config.habilitar_feedback else 'desativado'} com sucesso!", "success")
    return redirect(url_for("routes.dashboard"))

@routes.route('/feedback_ministrante/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def feedback_ministrante(oficina_id):
    # Verifica se o usuário é um ministrante
    if current_user.tipo != 'ministrante':
        flash('Apenas ministrantes podem enviar feedback por aqui.', 'danger')
        return redirect(url_for('routes.dashboard_ministrante'))
    
    oficina = Oficina.query.get_or_404(oficina_id)
    
    if request.method == 'POST':
        try:
            rating = int(request.form.get('rating', 0))
        except ValueError:
            rating = 0
        comentario = request.form.get('comentario', '').strip()
        if rating < 1 or rating > 5:
            flash('A avaliação deve ser entre 1 e 5 estrelas.', 'danger')
            return redirect(url_for('routes.feedback_ministrante', oficina_id=oficina_id))
        
        novo_feedback = Feedback(
            ministrante_id=current_user.id,  # Salva o id do ministrante
            oficina_id=oficina.id,
            rating=rating,
            comentario=comentario
        )
        db.session.add(novo_feedback)
        db.session.commit()
        flash('Feedback enviado com sucesso!', 'success')
        return redirect(url_for('routes.dashboard_ministrante'))
    
    # Reaproveita o template existente (feedback.html) ou crie um específico se desejar
    return render_template('feedback.html', oficina=oficina)


@routes.route('/gerar_certificado/<int:oficina_id>', methods=['GET'])
@login_required
def gerar_certificado_individual(oficina_id):
    """
    Gera um certificado individual para o usuário logado em uma oficina específica.
    """
    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash("Oficina não encontrada!", "danger")
        return redirect(url_for('routes.dashboard_participante'))

    # Verifica se o usuário está inscrito na oficina
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first()
    if not inscricao:
        flash("Você não está inscrito nesta oficina!", "danger")
        return redirect(url_for('routes.dashboard_participante'))

    # Define o caminho do certificado
    pdf_path = f"static/certificados/certificado_{current_user.id}_{oficina.id}.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Gera o certificado (mesmo layout do admin, mas apenas para o usuário logado)
    gerar_certificados_pdf(oficina, [inscricao], pdf_path)

    # Retorna o arquivo PDF gerado
    return send_file(pdf_path, as_attachment=True)


# ===========================
#   CADASTRO DE MINISTRANTE
# ===========================
import logging
from flask import Flask, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash
from extensions import db
from models import Ministrante

# Configure o logger (isso pode ser configurado globalmente no seu app)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@routes.route('/cadastro_ministrante', methods=['GET', 'POST'])
def cadastro_ministrante():
    if request.method == 'POST':
        print("Iniciando o cadastro de ministrante")
        
        # Coleta dos dados do formulário
        nome = request.form.get('nome')
        formacao = request.form.get('formacao')
        areas = request.form.get('areas')
        cpf = request.form.get('cpf')
        pix = request.form.get('pix')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        print(f"Dados recebidos - Nome: {nome}, Email: {email}, CPF: {cpf}")
        
        # Verifica se já existe um ministrante com o mesmo email
        existing_email = Ministrante.query.filter_by(email=email).first()
        if existing_email:
            logger.warning(f"E-mail já cadastrado: {email}")
            flash('Erro: Este e-mail já está cadastrado!', 'danger')
            return redirect(url_for('routes.cadastro_ministrante'))
        
        # Verifica se já existe um ministrante com o mesmo CPF
        existing_cpf = Ministrante.query.filter_by(cpf=cpf).first()
        if existing_cpf:
            logger.warning(f"CPF já cadastrado: {cpf}")
            flash('Erro: Este CPF já está cadastrado!', 'danger')
            return redirect(url_for('routes.cadastro_ministrante'))
        
        # Criação do novo ministrante
        novo_ministrante = Ministrante(
            nome=nome,
            formacao=formacao,
            areas_atuacao=areas,
            cpf=cpf,
            pix=pix,
            cidade=cidade,
            estado=estado,
            email=email,
            senha=generate_password_hash(senha)
        )
        
        try:
            print("Adicionando novo ministrante no banco de dados")
            db.session.add(novo_ministrante)
            db.session.commit()
            print("Ministrante cadastrado com sucesso!")
            flash('Cadastro realizado com sucesso!', 'success')
            return redirect(url_for('routes.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cadastrar ministrante: {e}", exc_info=True)
            flash('Erro ao cadastrar ministrante. Tente novamente.', 'danger')
            return redirect(url_for('routes.cadastro_ministrante'))
    
    return render_template('cadastro_ministrante.html')

@routes.route('/dashboard_ministrante')
@login_required
def dashboard_ministrante():
    # Log para depuração: exibir o tipo do current_user e seus atributos
    import logging
    logger = logging.getLogger(__name__)
    print(f"current_user: {current_user}, type: {type(current_user)}")
    # Se estiver usando UserMixin, current_user pode não ter o atributo 'tipo'
    # Então, usamos isinstance para verificar se é Ministrante.
    if not isinstance(current_user, Ministrante):
        print("current_user não é uma instância de Ministrante")
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.home'))

    # Busca o ministrante logado com base no email (ou use current_user diretamente)
    ministrante_logado = Ministrante.query.filter_by(email=current_user.email).first()
    if not ministrante_logado:
        print("Ministrante não encontrado no banco de dados")
        flash('Ministrante não encontrado!', 'danger')
        return redirect(url_for('routes.home'))

    # Buscar as oficinas deste ministrante
    oficinas_do_ministrante = Oficina.query.filter_by(ministrante_id=ministrante_logado.id).all()
    # Carrega a configuração e define habilitar_feedback
    config = Configuracao.query.first()
    habilitar_feedback = config.habilitar_feedback if config else False
    print(f"Foram encontradas {len(oficinas_do_ministrante)} oficinas para o ministrante {ministrante_logado.email}")

    return render_template(
        'dashboard_ministrante.html',
        ministrante=ministrante_logado,
        oficinas=oficinas_do_ministrante,
        habilitar_feedback=habilitar_feedback
    )

@routes.route('/enviar_relatorio/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def enviar_relatorio(oficina_id):
    if current_user.tipo != 'ministrante':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.home'))

    oficina = Oficina.query.get_or_404(oficina_id)
    ministrante_logado = Ministrante.query.filter_by(email=current_user.email).first()

    if oficina.ministrante_id != ministrante_logado.id:
        flash('Você não é responsável por esta oficina!', 'danger')
        return redirect(url_for('routes.dashboard_ministrante'))

    if request.method == 'POST':
        metodologia = request.form.get('metodologia')
        resultados = request.form.get('resultados')

        # Upload de fotos/vídeos se desejado
        arquivo_midia = request.files.get('arquivo_midia')
        midia_path = None
        if arquivo_midia:
            filename = secure_filename(arquivo_midia.filename)
            pasta_uploads = os.path.join('uploads', 'relatorios')
            os.makedirs(pasta_uploads, exist_ok=True)
            caminho_arquivo = os.path.join(pasta_uploads, filename)
            arquivo_midia.save(caminho_arquivo)
            midia_path = caminho_arquivo

        novo_relatorio = RelatorioOficina(
            oficina_id=oficina.id,
            ministrante_id=ministrante_logado.id,
            metodologia=metodologia,
            resultados=resultados,
            fotos_videos_path=midia_path
        )
        db.session.add(novo_relatorio)
        db.session.commit()

        flash("Relatório enviado com sucesso!", "success")
        return redirect(url_for('routes.dashboard_ministrante'))

    return render_template('enviar_relatorio.html', oficina=oficina)

@routes.route('/upload_material/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def upload_material(oficina_id):
    # Verifica se o usuário é um ministrante
    from models import Ministrante  # Certifique-se de importar se necessário
    if not hasattr(current_user, 'tipo') or current_user.tipo != 'ministrante':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.home'))
    
    # Buscar a oficina e verificar se o ministrante logado é responsável por ela
    oficina = Oficina.query.get_or_404(oficina_id)
    ministrante_logado = Ministrante.query.filter_by(email=current_user.email).first()
    if not ministrante_logado or oficina.ministrante_id != ministrante_logado.id:
        flash('Você não é responsável por esta oficina!', 'danger')
        return redirect(url_for('routes.dashboard_ministrante'))
    
    if request.method == 'POST':
        arquivo = request.files.get('arquivo')
        if arquivo:
            filename = secure_filename(arquivo.filename)
            pasta_uploads = os.path.join('uploads', 'materiais')
            os.makedirs(pasta_uploads, exist_ok=True)
            caminho_arquivo = os.path.join(pasta_uploads, filename)
            arquivo.save(caminho_arquivo)
            
            novo_material = MaterialOficina(
                oficina_id=oficina.id,
                nome_arquivo=filename,
                caminho_arquivo=caminho_arquivo
            )
            db.session.add(novo_material)
            db.session.commit()
            
            flash('Material anexado com sucesso!', 'success')
            return redirect(url_for('routes.dashboard_ministrante'))
        else:
            flash('Nenhum arquivo foi enviado.', 'danger')
    
    return render_template('upload_material.html', oficina=oficina)

@routes.route('/editar_ministrante/<int:ministrante_id>', methods=['GET', 'POST'])
@login_required
def editar_ministrante(ministrante_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
    
    ministrante = Ministrante.query.get_or_404(ministrante_id)
    
    if request.method == 'POST':
        # Coleta os dados do formulário
        ministrante.nome = request.form.get('nome')
        ministrante.formacao = request.form.get('formacao')
        ministrante.areas_atuacao = request.form.get('areas')
        ministrante.cpf = request.form.get('cpf')
        ministrante.pix = request.form.get('pix')
        ministrante.cidade = request.form.get('cidade')
        ministrante.estado = request.form.get('estado')
        ministrante.email = request.form.get('email')
        nova_senha = request.form.get('senha')
        if nova_senha:
            from werkzeug.security import generate_password_hash
            ministrante.senha = generate_password_hash(nova_senha)
        
        try:
            db.session.commit()
            flash('Ministrante atualizado com sucesso!', 'success')
            return redirect(url_for('routes.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar ministrante: {str(e)}', 'danger')
            return redirect(url_for('routes.editar_ministrante', ministrante_id=ministrante_id))
    
    return render_template('editar_ministrante.html', ministrante=ministrante)

@routes.route('/excluir_ministrante/<int:ministrante_id>', methods=['POST'])
@login_required
def excluir_ministrante(ministrante_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
    
    ministrante = Ministrante.query.get_or_404(ministrante_id)
    try:
        db.session.delete(ministrante)
        db.session.commit()
        flash('Ministrante excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir ministrante: {str(e)}', 'danger')
    return redirect(url_for('routes.dashboard'))

@routes.route('/gerenciar_ministrantes', methods=['GET'])
@login_required
def gerenciar_ministrantes():
    # Apenas administradores têm acesso a essa rota
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
    
    # Busca todos os ministrantes cadastrados
    ministrantes = Ministrante.query.all()
    return render_template('gerenciar_ministrantes.html', ministrantes=ministrantes)


@routes.route('/admin_scan')
@login_required
def admin_scan():
    if current_user.tipo not in ('admin', 'cliente'):  # Agora clientes podem acessar
        flash("Acesso negado!", "danger")
        return redirect(url_for('routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'routes.dashboard'))
    return render_template("scan_qr.html")

@routes.route('/relatorios/<path:filename>')
@login_required
def get_relatorio_file(filename):
    # Ajuste o caminho para a pasta de relatórios
    pasta_uploads = os.path.join('uploads', 'relatorios')
    return send_from_directory(pasta_uploads, filename)

@routes.route('/gerar_pdf_checkins_qr', methods=['GET'])
@login_required
def gerar_pdf_checkins_qr():
    # 1. Busca os Check-ins com palavra_chave="QR-AUTO"
    checkins_qr = Checkin.query.filter_by(palavra_chave='QR-AUTO').all()
    if not checkins_qr:
        flash("Não há check-ins via QR Code para gerar o PDF.", "warning")
        return redirect(url_for('routes.dashboard'))

    # 2. Define o caminho do PDF (pasta static/comprovantes, por ex.)
    pdf_filename = "checkins_via_qr.pdf"
    pdf_path = os.path.join("static", "comprovantes", pdf_filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # 3. Configura o Documento
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=30,
        bottomMargin=20
    )
    elements = []
    styles = getSampleStyleSheet()

    # 4. Título
    title_style = styles["Title"]
    title_para = Paragraph("Lista de Check-ins via QR Code", title_style)
    elements.append(title_para)
    elements.append(Spacer(1, 0.3 * inch))

    # 5. Monta a tabela
    # Cabeçalhos
    data_table = [["Nome", "E-mail", "Oficina", "Data/Hora Check-in"]]

    # Linhas do corpo
    for ck in checkins_qr:
        usuario = ck.usuario
        oficina = ck.oficina
        data_str = ck.data_hora.strftime('%d/%m/%Y %H:%M') if ck.data_hora else ""
        data_table.append([
            usuario.nome if usuario else "",
            usuario.email if usuario else "",
            oficina.titulo if oficina else "",
            data_str
        ])

    # 6. Cria o objeto Table (flowable) e estilo
    table = Table(
        data_table,
        colWidths=[2.0 * inch, 2.5 * inch, 2.5 * inch, 1.5 * inch]  # Ajuste conforme necessidade
    )

    table.setStyle(TableStyle([
        # Cabeçalho com fundo azul e texto branco
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),

        # Grid em toda a tabela
        ('GRID', (0, 0), (-1, -1), 1, colors.black),

        # Fonte do cabeçalho
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),

        # Alinhamento vertical
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Repete cabeçalho em cada página
        ('REPEATROWS', (0,0), (-1,0))
    ]))

    elements.append(table)

    # 7. Constrói o PDF (o ReportLab fará a quebra de página automática)
    doc.build(elements)

    # 8. Retorna para download
    return send_file(pdf_path, as_attachment=True)

@routes.route('/gerenciar_participantes', methods=['GET'])
@login_required
def gerenciar_participantes():
    # Verifique se é admin
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))

    # Busca todos os usuários cujo tipo é 'participante'
    participantes = Usuario.query.filter_by(tipo='participante').all()

    # Renderiza um template parcial (ou completo). Você pode renderizar
    # a página inteira ou só retornar JSON. Aqui vamos supor que renderiza a modal.
    return render_template('gerenciar_participantes.html', participantes=participantes)

@routes.route('/excluir_participante/<int:participante_id>', methods=['POST'])
@login_required
def excluir_participante(participante_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
    
    participante = Usuario.query.get_or_404(participante_id)
    if participante.tipo != 'participante':
        flash('Esse usuário não é um participante.', 'danger')
        return redirect(url_for('routes.dashboard'))
    
    db.session.delete(participante)
    db.session.commit()
    flash('Participante excluído com sucesso!', 'success')
    return redirect(url_for('routes.dashboard'))

@routes.route('/editar_participante_admin/<int:participante_id>', methods=['POST'])
@login_required
def editar_participante_admin(participante_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
    
    participante = Usuario.query.get_or_404(participante_id)
    if participante.tipo != 'participante':
        flash('Esse usuário não é um participante.', 'danger')
        return redirect(url_for('routes.dashboard'))

    # Captura os dados do form
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    email = request.form.get('email')
    formacao = request.form.get('formacao')
    nova_senha = request.form.get('senha')

    # Atualiza
    participante.nome = nome
    participante.cpf = cpf
    participante.email = email
    participante.formacao = formacao
    if nova_senha:
        participante.senha = generate_password_hash(nova_senha)

    db.session.commit()
    flash('Participante atualizado com sucesso!', 'success')
    return redirect(url_for('routes.dashboard'))

@routes.route('/gerar_relatorio_mensagem', methods=['GET'])
@login_required
def gerar_relatorio_mensagem():
    from sqlalchemy import func
    
    # Se quiser só as oficinas do cliente, verifique se current_user é admin ou cliente:
    is_admin = (current_user.tipo == 'admin')
    if is_admin:
        total_oficinas = Oficina.query.count()
        total_vagas = db.session.query(func.sum(Oficina.vagas)).scalar() or 0
        total_inscricoes = Inscricao.query.count()
        oficinas_list = Oficina.query.all()
    else:
        total_oficinas = Oficina.query.filter_by(cliente_id=current_user.id).count()
        total_vagas = db.session.query(func.sum(Oficina.vagas)).filter(Oficina.cliente_id == current_user.id).scalar() or 0
        total_inscricoes = Inscricao.query.join(Oficina).filter(Oficina.cliente_id == current_user.id).count()
        oficinas_list = Oficina.query.filter_by(cliente_id=current_user.id).all()
    
    # Cálculo de adesão
    percentual_adesao = (total_inscricoes / total_vagas) * 100 if total_vagas > 0 else 0

    # Monta a mensagem com emojis e loop
    mensagem = (
        "📊 *Relatório do Sistema*\n\n"
        f"✅ *Total de Oficinas:* {total_oficinas}\n"
        f"✅ *Vagas Ofertadas:* {total_vagas}\n"
        f"✅ *Vagas Preenchidas:* {total_inscricoes}\n"
        f"✅ *% de Adesão:* {percentual_adesao:.2f}%\n\n"
        "----------------------------------------\n"
        "📌 *DADOS POR OFICINA:*\n"
    )

    for oficina in oficinas_list:
        # Conta inscritos
        num_inscritos = Inscricao.query.filter_by(oficina_id=oficina.id).count()
        ocupacao = (num_inscritos / oficina.vagas)*100 if oficina.vagas else 0
        
        mensagem += (
            f"\n🎓 *Oficina:* {oficina.titulo}\n"
            f"🔹 *Vagas:* {oficina.vagas}\n"
            f"🔹 *Inscritos:* {num_inscritos}\n"
            f"🔹 *Ocupação:* {ocupacao:.2f}%\n"
        )

    return mensagem


@routes.route('/cancelar_inscricoes_lote', methods=['POST'])
@login_required
def cancelar_inscricoes_lote():
    # Verifica se é admin
    if current_user.tipo != 'admin':
        flash("Acesso negado!", "danger")
        return redirect(url_for('routes.dashboard'))

    # Pega os IDs marcados
    inscricao_ids = request.form.getlist('inscricao_ids')
    if not inscricao_ids:
        flash("Nenhuma inscrição selecionada!", "warning")
        return redirect(url_for('routes.dashboard'))

    # Converte para int
    inscricao_ids = list(map(int, inscricao_ids))

    try:
        # Busca todas as inscrições com esses IDs
        inscricoes = Inscricao.query.filter(Inscricao.id.in_(inscricao_ids)).all()
        # Cancela removendo do banco
        for insc in inscricoes:
            db.session.delete(insc)

        db.session.commit()
        flash(f"Foram canceladas {len(inscricoes)} inscrições!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao cancelar inscrições: {e}", "danger")

    return redirect(url_for('routes.dashboard'))


@routes.route('/mover_inscricoes_lote', methods=['POST'])
@login_required
def mover_inscricoes_lote():
    if current_user.tipo != 'admin':
        flash("Acesso negado!", "danger")
        return redirect(url_for('routes.dashboard'))

    inscricao_ids = request.form.getlist('inscricao_ids')
    if not inscricao_ids:
        flash("Nenhuma inscrição selecionada!", "warning")
        return redirect(url_for('routes.dashboard'))
    
    oficina_destino_id = request.form.get('oficina_destino')
    if not oficina_destino_id:
        flash("Nenhuma oficina de destino selecionada!", "warning")
        return redirect(url_for('routes.dashboard'))

    # Converte os ids
    inscricao_ids = list(map(int, inscricao_ids))
    oficina_destino_id = int(oficina_destino_id)

    # Verifica se a oficina existe
    oficina_destino = Oficina.query.get(oficina_destino_id)
    if not oficina_destino:
        flash("Oficina de destino não encontrada!", "danger")
        return redirect(url_for('routes.dashboard'))

    try:
        # Busca as inscrições
        inscricoes = Inscricao.query.filter(Inscricao.id.in_(inscricao_ids)).all()

        # (Opcional) verifique se oficina_destino tem vagas suficientes, se for caso
        # Exemplo: se oficina_destino.vagas < len(inscricoes), ...
        # mas lembre que você pode já ter decrementado as vagas no momento em que
        # usuário se inscreve. Precisaria de uma lógica de "vagas" robusta.

        # Atualiza a oficina
        for insc in inscricoes:
            # 1) Incrementa a vaga na oficina atual (opcional, se você decrementou ao inscrever)
            oficina_origem = insc.oficina
            oficina_origem.vagas += 1  # se estiver usando contagem de vagas "ao vivo"

            # 2) Decrementa a vaga na oficina destino
            oficina_destino.vagas -= 1

            # 3) Move a inscrição
            insc.oficina_id = oficina_destino_id

        db.session.commit()
        flash(f"Foram movidas {len(inscricoes)} inscrições para a oficina {oficina_destino.titulo}!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao mover inscrições: {e}", "danger")

    return redirect(url_for('routes.dashboard'))

@routes.route('/cancelar_inscricao/<int:inscricao_id>', methods=['GET','POST'])
@login_required
def cancelar_inscricao(inscricao_id):
    if current_user.tipo != 'admin':
        flash("Acesso negado!", "danger")
        return redirect(url_for('routes.dashboard'))
    insc = Inscricao.query.get_or_404(inscricao_id)
    try:
        db.session.delete(insc)
        db.session.commit()
        flash("Inscrição cancelada com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao cancelar inscrição: {e}", "danger")

    return redirect(url_for('routes.dashboard'))

@routes.route('/dashboard_cliente')
@login_required
def dashboard_cliente():
    if current_user.tipo != 'cliente':
        return redirect(url_for('routes.dashboard'))

    print(f"📌 [DEBUG] Cliente autenticado: {current_user.email} (ID: {current_user.id})")

    # Mostra apenas as oficinas criadas por este cliente OU pelo admin (cliente_id nulo)
    oficinas = Oficina.query.filter_by(cliente_id=current_user.id).options(
        db.joinedload(Oficina.inscritos).joinedload(Inscricao.usuario)
    ).all()
    # Cálculo das estatísticas
    total_oficinas = len(oficinas)
    total_vagas = sum(of.vagas for of in oficinas)
    total_inscricoes = Inscricao.query.join(Oficina).filter(
        (Oficina.cliente_id == current_user.id) | (Oficina.cliente_id.is_(None))
    ).count()
    percentual_adesao = (total_inscricoes / total_vagas) * 100 if total_vagas > 0 else 0

    checkins_via_qr = Checkin.query.join(Oficina).filter(
        (Oficina.cliente_id == current_user.id) | (Oficina.cliente_id.is_(None))
    ).all()

    inscritos = Inscricao.query.join(Oficina).filter(
        (Oficina.cliente_id == current_user.id) | (Oficina.cliente_id.is_(None))
    ).all()

    return render_template(
        'dashboard_cliente.html',
        usuario=current_user,
        oficinas=oficinas,
        total_oficinas=total_oficinas,
        total_vagas=total_vagas,
        total_inscricoes=total_inscricoes,
        percentual_adesao=percentual_adesao,
        checkins_via_qr=checkins_via_qr,
        inscritos=inscritos
    )



@app.route('/oficinas_disponiveis')
@login_required
def oficinas_disponiveis():
    oficinas = Oficina.query.filter_by(cliente_id=current_user.cliente_id).all()
    return render_template('oficinas.html', oficinas=oficinas)

@routes.route('/gerar_link', methods=['GET'])
@login_required
def gerar_link():
    if session.get('user_type') not in ['cliente', 'admin']:
        return "Forbidden", 403
    
    cliente_id = current_user.id
    novo_token = str(uuid.uuid4())

    # Criar o link de cadastro no banco
    novo_link = LinkCadastro(cliente_id=cliente_id, token=novo_token)
    db.session.add(novo_link)
    db.session.commit()

    # Detecta se está rodando localmente ou no Render
    if request.host.startswith("127.0.0.1") or "localhost" in request.host:
        base_url = "http://127.0.0.1:5000"  # URL local
    else:
        base_url = "https://appfiber.com.br"  # URL do Render

    # Criar o link apontando para /cadastro_participante?token=TOKEN
    link_gerado = f"{base_url}{url_for('routes.cadastro_participante', token=novo_token)}"

    return link_gerado  # Retorna apenas o link para ser exibido no modal



@app.route('/inscricao/<token>', methods=['GET', 'POST'])
def inscricao(token):
    cliente = Cliente.query.filter_by(token=token).first()
    
    if not cliente:
        return "Link inválido", 404

    if request.method == 'POST':
        novo_usuario = Usuario(
            email=request.form['email'],
            senha_hash=generate_password_hash(request.form['senha']),
            cliente_id=cliente.id,
            tipo="usuario"
        )
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('inscricao.html', cliente=cliente)

@app.route('/superadmin_dashboard')
@login_required
def superadmin_dashboard():
    if not current_user.is_superuser():
        return abort(403)

    clientes = Cliente.query.all()
    return render_template('dashboard_superadmin.html', clientes=clientes)


@routes.route('/toggle_cliente/<int:cliente_id>')
@login_required
def toggle_cliente(cliente_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
    
    cliente = Cliente.query.get_or_404(cliente_id)
    cliente.ativo = not cliente.ativo  # Alterna o estado (True -> False ou False -> True)
    db.session.commit()
    flash(f"Cliente {'ativado' if cliente.ativo else 'desativado'} com sucesso", "success")
    return redirect(url_for('routes.dashboard'))


@routes.route('/cadastrar_cliente', methods=['GET', 'POST'])
@login_required
def cadastrar_cliente():
    if session.get('user_type') != 'admin':  # Apenas admin pode cadastrar clientes
        abort(403)

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        # Verifica se o e-mail já está cadastrado
        cliente_existente = Cliente.query.filter_by(email=email).first()
        if cliente_existente:
            flash("Já existe um cliente com esse e-mail!", "danger")
            return redirect(url_for('routes.cadastrar_cliente'))

        # Cria o cliente
        novo_cliente = Cliente(
            nome=request.form['nome'],
            email=request.form['email'],
            senha=request.form['senha']  # ✅ CORRETO
        )


        db.session.add(novo_cliente)
        db.session.commit()

        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for('routes.dashboard'))

    return render_template('cadastrar_cliente.html')


@routes.route('/oficinas', methods=['GET'])
@login_required
def listar_oficinas():
    if session.get('user_type') == 'participante':
        oficinas = Oficina.query.filter_by(cliente_id=current_user.cliente_id).all()  # ✅ Mostra apenas oficinas do Cliente que registrou o usuário
    else:
        oficinas = Oficina.query.all()

    return render_template('oficinas.html', oficinas=oficinas)

@routes.route('/editar_cliente/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))

    cliente = Cliente.query.get_or_404(cliente_id)
    if request.method == 'POST':
        cliente.nome = request.form.get('nome')
        cliente.email = request.form.get('email')
        nova_senha = request.form.get('senha')
        if nova_senha:  # Só atualiza a senha se ela for fornecida
            cliente.senha = generate_password_hash(nova_senha)
        try:
            db.session.commit()
            flash("Cliente atualizado com sucesso!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar cliente: {str(e)}", "danger")
        return redirect(url_for('routes.dashboard'))
    
    return render_template('editar_cliente.html', cliente=cliente)

@routes.route('/excluir_cliente/<int:cliente_id>', methods=['POST'])
@login_required
def excluir_cliente(cliente_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
    
    logger.info(f"Tentando excluir cliente ID: {cliente_id}")
    cliente = Cliente.query.get_or_404(cliente_id)
    try:
        db.session.delete(cliente)
        db.session.commit()
        flash("Cliente excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir cliente {cliente_id}: {str(e)}")
        flash(f"Erro ao excluir cliente: {str(e)}", "danger")
    return redirect(url_for('routes.dashboard'))

@routes.route('/formularios', methods=['GET'])
@login_required
def listar_formularios():
    formularios = Formulario.query.filter_by(cliente_id=current_user.id).all()
    return render_template('formularios.html', formularios=formularios)

@routes.route('/formularios/novo', methods=['GET', 'POST'])
@login_required
def criar_formulario():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        
        novo_formulario = Formulario(
            nome=nome,
            descricao=descricao,
            cliente_id=current_user.id  # Relaciona com o cliente logado
        )
        db.session.add(novo_formulario)
        db.session.commit()
        flash('Formulário criado com sucesso!', 'success')
        return redirect(url_for('routes.listar_formularios'))
    
    return render_template('criar_formulario.html')

@routes.route('/formularios/<int:formulario_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_formulario(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)

    if request.method == 'POST':
        formulario.nome = request.form.get('nome')
        formulario.descricao = request.form.get('descricao')
        db.session.commit()
        flash('Formulário atualizado!', 'success')
        return redirect(url_for('routes.listar_formularios'))

    return render_template('editar_formulario.html', formulario=formulario)

@routes.route('/formularios/<int:formulario_id>/deletar', methods=['POST'])
@login_required
def deletar_formulario(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)
    db.session.delete(formulario)
    db.session.commit()
    flash('Formulário deletado com sucesso!', 'success')
    return redirect(url_for('routes.listar_formularios'))

@routes.route('/formularios/<int:formulario_id>/campos', methods=['GET', 'POST'])
@login_required
def gerenciar_campos(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)

    if request.method == 'POST':
        nome = request.form.get('nome')
        tipo = request.form.get('tipo')
        opcoes = request.form.get('opcoes', '').strip()
        obrigatorio = request.form.get('obrigatorio') == 'on'
        tamanho_max = request.form.get('tamanho_max') or None
        regex_validacao = request.form.get('regex_validacao') or None

        novo_campo = CampoFormulario(
            formulario_id=formulario.id,
            nome=nome,
            tipo=tipo,
            opcoes=opcoes if tipo in ['dropdown', 'checkbox', 'radio'] else None,
            obrigatorio=obrigatorio,
            tamanho_max=int(tamanho_max) if tamanho_max else None,
            regex_validacao=regex_validacao
        )

        db.session.add(novo_campo)
        db.session.commit()
        flash('Campo adicionado com sucesso!', 'success')

        return redirect(url_for('routes.gerenciar_campos', formulario_id=formulario.id))

    return render_template('gerenciar_campos.html', formulario=formulario)

@routes.route('/campos/<int:campo_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_campo(campo_id):
    campo = CampoFormulario.query.get_or_404(campo_id)

    if request.method == 'POST':
        campo.nome = request.form.get('nome')
        campo.tipo = request.form.get('tipo')
        campo.opcoes = request.form.get('opcoes', '').strip() if campo.tipo in ['dropdown', 'checkbox', 'radio'] else None
        campo.obrigatorio = request.form.get('obrigatorio') == 'on'
        campo.tamanho_max = request.form.get('tamanho_max') or None
        campo.regex_validacao = request.form.get('regex_validacao') or None

        db.session.commit()
        flash('Campo atualizado com sucesso!', 'success')

        return redirect(url_for('routes.gerenciar_campos', formulario_id=campo.formulario_id))

    return render_template('editar_campo.html', campo=campo)

@routes.route('/campos/<int:campo_id>/deletar', methods=['POST'])
@login_required
def deletar_campo(campo_id):
    campo = CampoFormulario.query.get_or_404(campo_id)
    formulario_id = campo.formulario_id
    db.session.delete(campo)
    db.session.commit()
    flash('Campo removido com sucesso!', 'success')

    return redirect(url_for('routes.gerenciar_campos', formulario_id=formulario_id))

@routes.route('/formularios/<int:formulario_id>/preencher', methods=['GET', 'POST'])
@login_required
def preencher_formulario(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)

    if request.method == 'POST':
        resposta_formulario = RespostaFormulario(
            formulario_id=formulario.id,
            usuario_id=current_user.id
        )
        db.session.add(resposta_formulario)
        db.session.commit()

        for campo in formulario.campos:
            valor = request.form.get(str(campo.id))
            if campo.tipo == 'file' and 'file_' + str(campo.id) in request.files:
                arquivo = request.files['file_' + str(campo.id)]
                if arquivo.filename:
                    filename = secure_filename(arquivo.filename)
                    caminho_arquivo = os.path.join('uploads', 'respostas', filename)
                    os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
                    arquivo.save(caminho_arquivo)
                    valor = caminho_arquivo  # Salva o caminho do arquivo

            resposta_campo = RespostaCampo(
                resposta_formulario_id=resposta_formulario.id,
                campo_id=campo.id,
                valor=valor
            )
            db.session.add(resposta_campo)

        db.session.commit()
        flash("Formulário enviado com sucesso!", "success")
        return redirect(url_for('routes.dashboard_participante'))

    return render_template('preencher_formulario.html', formulario=formulario)

@routes.route('/formularios/<int:formulario_id>/respostas', methods=['GET'])
@login_required
def listar_respostas(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)
    respostas = RespostaFormulario.query.filter_by(formulario_id=formulario.id).all()

    return render_template('listar_respostas.html', formulario=formulario, respostas=respostas)

@routes.route('/formularios_participante', methods=['GET'])
@login_required
def listar_formularios_participante():
    if current_user.tipo != 'participante':
        flash("Acesso negado!", "danger")
        return redirect(url_for('routes.dashboard'))

    # Busca apenas formulários disponíveis para o participante
    formularios = Formulario.query.all()

    if not formularios:
        flash("Nenhum formulário disponível no momento.", "warning")
        return redirect(url_for('routes.dashboard_participante'))

    return render_template('formularios_participante.html', formularios=formularios)

@routes.route('/respostas/<int:resposta_id>', methods=['GET'])
@login_required
def visualizar_resposta(resposta_id):
    resposta = RespostaFormulario.query.get_or_404(resposta_id)
    return render_template('visualizar_resposta.html', resposta=resposta)

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

@routes.route('/formularios/<int:formulario_id>/exportar_pdf')
@login_required
def gerar_pdf_respostas(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)
    respostas = RespostaFormulario.query.filter_by(formulario_id=formulario.id).all()

    pdf_filename = f"respostas_{formulario.id}.pdf"
    pdf_path = f"static/{pdf_filename}"

    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, f"Respostas do Formulário: {formulario.nome}")

    y = 720
    for resposta in respostas:
        c.setFont("Helvetica", 12)
        c.drawString(100, y, f"Usuário: {resposta.usuario.nome} - Enviado em {resposta.data_submissao.strftime('%d/%m/%Y %H:%M')}")
        y -= 20
        for campo in resposta.respostas_campos:
            c.drawString(120, y, f"{campo.campo.nome}: {campo.valor}")
            y -= 15
        y -= 10

        if y < 50:  # Se estiver perto do final da página, cria uma nova
            c.showPage()
            y = 750

    c.save()
    return send_file(pdf_path, as_attachment=True)

@routes.route('/formularios/<int:formulario_id>/exportar_csv')
@login_required
def exportar_csv(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)
    respostas = RespostaFormulario.query.filter_by(formulario_id=formulario.id).all()

    csv_filename = f"respostas_{formulario.id}.csv"
    
    def generate():
        data = csv.writer(Response(), delimiter=',')
        data.writerow(["Usuário", "Data de Envio"] + [campo.nome for campo in formulario.campos])

        for resposta in respostas:
            row = [resposta.usuario.nome, resposta.data_submissao.strftime('%d/%m/%Y %H:%M')]
            for campo in formulario.campos:
                valor = next((resp.valor for resp in resposta.respostas_campos if resp.campo_id == campo.id), "")
                row.append(valor)
            data.writerow(row)
        
        return data

    response = Response(generate(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={csv_filename}"
    return response