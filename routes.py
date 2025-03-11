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
from utils import enviar_email
from datetime import datetime
from flask_mail import Message
from models import Evento

# Extensões e modelos (utilize sempre o mesmo ponto de importação para o db)
from extensions import db, login_manager
from models import (Usuario, Oficina, Inscricao, OficinaDia, Checkin,
                    Configuracao, Feedback, Ministrante, RelatorioOficina, MaterialOficina, ConfiguracaoCliente, FeedbackCampo, RespostaFormulario, RespostaCampo, InscricaoTipo)
from utils import obter_estados, obter_cidades, gerar_qr_code, gerar_qr_code_inscricao, gerar_comprovante_pdf, gerar_etiquetas_pdf  # Funções auxiliares
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
from collections import defaultdict
from datetime import datetime


# ReportLab para PDFs
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, LongTable
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
@routes.route('/inscricao/<path:identifier>', methods=['GET', 'POST'])  # Aceita slug ou token
def cadastro_participante(identifier=None):
    from collections import defaultdict
    from datetime import datetime

    alert = None
    cliente_id = None
    evento = None
    token = request.args.get('token') if not identifier else identifier  # Pega o token da URL ou usa o identifier

    # 1) Inicializa variáveis
    sorted_keys = []
    grouped_oficinas = {}
    oficinas = []

    # Busca o link pelo token ou slug
    link = None
    if token:
        link = LinkCadastro.query.filter(
            (LinkCadastro.token == token) | 
            (LinkCadastro.slug_customizado == token)
        ).first()

    if not link:
        flash("Erro: Link de cadastro inválido ou expirado!", "danger")
        return redirect(url_for('routes.cadastro_participante'))

    cliente_id = link.cliente_id
    evento = Evento.query.get(link.evento_id) if link.evento_id else None

    if evento:
        # Carrega oficinas do evento
        oficinas = Oficina.query.filter_by(evento_id=evento.id).all()
    else:
        # Fallback: carrega oficinas do cliente se não houver evento associado
        oficinas = Oficina.query.filter_by(cliente_id=cliente_id).all()

    # Agrupa oficinas por data
    temp_group = defaultdict(list)
    for oficina in oficinas:
        for dia in oficina.dias:
            data_str = dia.data.strftime('%d/%m/%Y')
            temp_group[data_str].append({
                'titulo': oficina.titulo,
                'descricao': oficina.descricao,
                'ministrante': oficina.ministrante_obj.nome if oficina.ministrante_obj else '',
                'horario_inicio': dia.horario_inicio,
                'horario_fim': dia.horario_fim
            })

    # Ordena as atividades por horário de início para cada data
    for date_str in temp_group:
        temp_group[date_str].sort(key=lambda x: x['horario_inicio'])

    sorted_keys = sorted(temp_group.keys(), key=lambda d: datetime.strptime(d, '%d/%m/%Y'))
    grouped_oficinas = temp_group

    if request.method == 'POST':
        # Lógica de cadastro do participante
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        senha = request.form.get('senha')
        formacao = request.form.get('formacao')
        estados = request.form.getlist('estados[]')
        cidades = request.form.getlist('cidades[]')
        estados_str = ','.join(estados) if estados else ''
        cidades_str = ','.join(cidades) if cidades else ''

        # Verifica se todos os campos obrigatórios foram preenchidos
        if not all([nome, cpf, email, senha, formacao]):
            flash('Erro: Todos os campos obrigatórios devem ser preenchidos!', 'danger')
            return render_template(
                'cadastro_participante.html',
                alert={"category": "danger", "message": "Todos os campos obrigatórios devem ser preenchidos!"},
                token=link.token,
                evento=evento,
                sorted_keys=sorted_keys,
                grouped_oficinas=grouped_oficinas
            )

        # Verifica se o e-mail já existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash('Erro: Este e-mail já está cadastrado!', 'danger')
            return render_template(
                'cadastro_participante.html',
                alert={"category": "danger", "message": "Este e-mail já está cadastrado!"},
                token=link.token,
                evento=evento,
                sorted_keys=sorted_keys,
                grouped_oficinas=grouped_oficinas
            )

        # Verifica se o CPF já existe
        usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
        if usuario_existente:
            alert = {"category": "danger", "message": "CPF já está sendo usado por outro usuário!"}
        else:
            novo_usuario = Usuario(
                nome=nome,
                cpf=cpf,
                email=email,
                senha=generate_password_hash(senha),  # Usando generate_password_hash diretamente
                formacao=formacao,
                tipo='participante',
                estados=estados_str,
                cidades=cidades_str,
                cliente_id=cliente_id  # Vincula ao cliente do link
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

    # Renderiza o template
    return render_template(
        'cadastro_participante.html',
        alert=alert,
        token=link.token,
        evento=evento,
        sorted_keys=sorted_keys,
        grouped_oficinas=grouped_oficinas
    )

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
    cliente_filter = request.args.get('cliente_id', '').strip()

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
            'id': of.id,  # ✅ Adicionando ID da oficina
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
    if is_admin and cliente_filter:
        query = query.filter(Oficina.cliente_id == cliente_filter)
    oficinas_filtradas = query.all()

    # Estatísticas de oficinas (aplicando filtro)
    lista_oficinas_info = []
    for of in oficinas_filtradas:
        num_inscritos = Inscricao.query.filter_by(oficina_id=of.id).count()
        perc_ocupacao = (num_inscritos / of.vagas) * 100 if of.vagas > 0 else 0

        lista_oficinas_info.append({
            'id': of.id,
            'titulo': of.titulo,
            'vagas': of.vagas,
            'inscritos': num_inscritos,
            'ocupacao': perc_ocupacao
        })

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
            'dias': dias,
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
        clientes=clientes,
        cliente_filter=cliente_filter
    )

@routes.route('/dashboard_participante')
@login_required
def dashboard_participante():
    print("DEBUG -> current_user.tipo =", current_user.tipo)  # <-- ADICIONE
    if current_user.tipo != 'participante':
        return redirect(url_for('routes.dashboard'))

    # Se o participante está associado a um cliente, buscamos a config desse cliente
    config_cliente = None
    # Verifica se há formulários disponíveis para preenchimento
    formularios_disponiveis = Formulario.query.count() > 0
    
    if current_user.cliente_id:
        from models import ConfiguracaoCliente  # certifique-se de importar se não estiver no topo
        config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=current_user.cliente_id).first()
        # Se não existir ainda, pode criar com valores padrão
        if not config_cliente:
            config_cliente = ConfiguracaoCliente(
                cliente_id=current_user.cliente_id,
                permitir_checkin_global=False,
                habilitar_feedback=False,
                habilitar_certificado_individual=False
            )
            db.session.add(config_cliente)
            db.session.commit()
    
    # Agora definimos as variáveis que o template utiliza
    permitir_checkin = config_cliente.permitir_checkin_global if config_cliente else False
    habilitar_feedback = config_cliente.habilitar_feedback if config_cliente else False
    habilitar_certificado = config_cliente.habilitar_certificado_individual if config_cliente else False

    # Busca as oficinas disponíveis
    if current_user.cliente_id:
        oficinas = Oficina.query.filter(
            (Oficina.cliente_id == current_user.cliente_id) | (Oficina.cliente_id == None)
        ).all()
    else:
        # Se o participante não tiver cliente_id, exibe apenas oficinas do admin
        oficinas = Oficina.query.filter(Oficina.cliente_id == None).all()

    # Monte a lista de inscricoes para controlar o que já está inscrito
    inscricoes_ids = [i.oficina_id for i in current_user.inscricoes]

    # Monte a estrutura que o template “dashboard_participante.html” precisa
    oficinas_formatadas = []
    for oficina in oficinas:
        dias = OficinaDia.query.filter_by(oficina_id=oficina.id).all()
        oficinas_formatadas.append({
            'id': oficina.id,
            'titulo': oficina.titulo,
            'descricao': oficina.descricao,
            'ministrante': oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A',
            'vagas': oficina.vagas,
            'carga_horaria': oficina.carga_horaria,
            'dias': dias
        })

    return render_template(
        'dashboard_participante.html',
        usuario=current_user,
        oficinas=oficinas_formatadas,
        # Aqui passamos as booleans *do cliente* para o template
        permitir_checkin_global=permitir_checkin,
        habilitar_feedback=habilitar_feedback,
        habilitar_certificado_individual=habilitar_certificado,
        formularios_disponiveis=formularios_disponiveis
    )



# ===========================
#    GESTÃO DE OFICINAS - ADMIN
# ===========================
@routes.route('/criar_oficina', methods=['GET', 'POST'])
@login_required
def criar_oficina():
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))

    estados = obter_estados()
    ministrantes_disponiveis = (
        Ministrante.query.filter_by(cliente_id=current_user.id).all()
        if current_user.tipo == 'cliente'
        else Ministrante.query.all()
    )
    clientes_disponiveis = Cliente.query.all() if current_user.tipo == 'admin' else []
    eventos_disponiveis = (
        Evento.query.filter_by(cliente_id=current_user.id).all()
        if current_user.tipo == 'cliente'
        else Evento.query.all()
    )

    if request.method == 'POST':
        print("Dados recebidos do formulário:", request.form)  # Log para depuração

        # Captura os campos do formulário
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        ministrante_id = request.form.get('ministrante_id') or None
        vagas = request.form.get('vagas')
        carga_horaria = request.form.get('carga_horaria')
        estado = request.form.get('estado')
        cidade = request.form.get('cidade')
        opcoes_checkin = request.form.get('opcoes_checkin')
        palavra_correta = request.form.get('palavra_correta')
        evento_id = request.form.get('evento_id')

        # Validação básica dos campos obrigatórios
        if not all([titulo, descricao, vagas, carga_horaria, estado, cidade, evento_id]):
            flash("Erro: Todos os campos obrigatórios devem ser preenchidos!", "danger")
            return render_template(
                'criar_oficina.html',
                estados=estados,
                ministrantes=ministrantes_disponiveis,
                clientes=clientes_disponiveis,
                eventos=eventos_disponiveis,
                datas=request.form.getlist('data[]'),
                horarios_inicio=request.form.getlist('horario_inicio[]'),
                horarios_fim=request.form.getlist('horario_fim[]')
            )

        # Definir o cliente da oficina
        cliente_id = (
            request.form.get('cliente_id') if current_user.tipo == 'admin' else current_user.id
        )

        # Verifica se o cliente possui habilitação de pagamento
        inscricao_gratuita = (
            True if request.form.get('inscricao_gratuita') == 'on' else False
            if current_user.habilita_pagamento else True
        )

        try:
            # Cria a nova oficina
            nova_oficina = Oficina(
                titulo=titulo,
                descricao=descricao,
                ministrante_id=ministrante_id,
                vagas=int(vagas),
                carga_horaria=carga_horaria,
                estado=estado,
                cidade=cidade,
                cliente_id=cliente_id,
                evento_id=evento_id,
                opcoes_checkin=opcoes_checkin,
                palavra_correta=palavra_correta
            )
            nova_oficina.inscricao_gratuita = inscricao_gratuita
            db.session.add(nova_oficina)
            db.session.flush()  # Garante que o ID da oficina esteja disponível

            # Adiciona os tipos de inscrição (se não for gratuita)
            if not inscricao_gratuita:
                nomes_tipos = request.form.getlist('nome_tipo[]')
                precos = request.form.getlist('preco_tipo[]')
                if not nomes_tipos or not precos:
                    raise ValueError("Tipos de inscrição e preços são obrigatórios para oficinas pagas.")
                for nome, preco in zip(nomes_tipos, precos):
                    novo_tipo = InscricaoTipo(
                        oficina_id=nova_oficina.id,
                        nome=nome,
                        preco=float(preco)
                    )
                    db.session.add(novo_tipo)

            # Adiciona os dias e horários
            datas = request.form.getlist('data[]')
            horarios_inicio = request.form.getlist('horario_inicio[]')
            horarios_fim = request.form.getlist('horario_fim[]')
            if not datas or len(datas) != len(horarios_inicio) or len(datas) != len(horarios_fim):
                raise ValueError("Datas e horários inconsistentes.")
            for i in range(len(datas)):
                novo_dia = OficinaDia(
                    oficina_id=nova_oficina.id,
                    data=datetime.strptime(datas[i], '%Y-%m-%d').date(),
                    horario_inicio=horarios_inicio[i],
                    horario_fim=horarios_fim[i]
                )
                db.session.add(novo_dia)

            db.session.commit()
            flash('Oficina criada com sucesso!', 'success')
            return redirect(
                url_for('routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'routes.dashboard')
            )

        except Exception as e:
            db.session.rollback()
            print(f"Erro ao criar oficina: {str(e)}")  # Log do erro
            flash(f"Erro ao criar oficina: {str(e)}", "danger")
            return render_template(
                'criar_oficina.html',
                estados=estados,
                ministrantes=ministrantes_disponiveis,
                clientes=clientes_disponiveis,
                eventos=eventos_disponiveis,
                datas=request.form.getlist('data[]'),
                horarios_inicio=request.form.getlist('horario_inicio[]'),
                horarios_fim=request.form.getlist('horario_fim[]')
            )

    return render_template(
        'criar_oficina.html',
        estados=estados,
        ministrantes=ministrantes_disponiveis,
        clientes=clientes_disponiveis,
        eventos=eventos_disponiveis
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

    if current_user.tipo == 'cliente' and oficina.cliente_id != current_user.id:
        flash('Você não tem permissão para editar esta oficina.', 'danger')
        return redirect(url_for('routes.dashboard_cliente'))

    estados = obter_estados()
    if current_user.tipo == 'cliente':
        ministrantes = Ministrante.query.filter_by(cliente_id=current_user.id).all()
        eventos_disponiveis = Evento.query.filter_by(cliente_id=current_user.id).all()
    else:
        ministrantes = Ministrante.query.all()
        eventos_disponiveis = Evento.query.all()

    clientes_disponiveis = Cliente.query.all() if current_user.tipo == 'admin' else []

    if request.method == 'POST':
        oficina.titulo = request.form.get('titulo')
        oficina.descricao = request.form.get('descricao')
        ministrante_id = request.form.get('ministrante_id') or None
        oficina.ministrante_id = ministrante_id
        oficina.vagas = int(request.form.get('vagas'))
        oficina.carga_horaria = request.form.get('carga_horaria')
        oficina.estado = request.form.get('estado')
        oficina.cidade = request.form.get('cidade')
        oficina.opcoes_checkin = request.form.get('opcoes_checkin')
        oficina.palavra_correta = request.form.get('palavra_correta')
        oficina.evento_id = request.form.get('evento_id')  # Atualiza o evento_id

        # Permitir que apenas admins alterem o cliente
        if current_user.tipo == 'admin':
            oficina.cliente_id = request.form.get('cliente_id') or None

        try:
            # Atualizar os dias e horários
            datas = request.form.getlist('data[]')
            horarios_inicio = request.form.getlist('horario_inicio[]')
            horarios_fim = request.form.getlist('horario_fim[]')

            if not datas or len(datas) != len(horarios_inicio) or len(datas) != len(horarios_fim):
                raise ValueError("Datas e horários inconsistentes.")

            # Apagar os registros antigos para evitar duplicação
            OficinaDia.query.filter_by(oficina_id=oficina.id).delete()

            for i in range(len(datas)):
                novo_dia = OficinaDia(
                    oficina_id=oficina.id,
                    data=datetime.strptime(datas[i], '%Y-%m-%d').date(),
                    horario_inicio=horarios_inicio[i],
                    horario_fim=horarios_fim[i]
                )
                db.session.add(novo_dia)

            db.session.commit()
            flash('Oficina editada com sucesso!', 'success')
            return redirect(url_for('routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'routes.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar oficina: {str(e)}', 'danger')
            return render_template(
                'editar_oficina.html',
                oficina=oficina,
                estados=estados,
                ministrantes=ministrantes,
                clientes=clientes_disponiveis,
                eventos=eventos_disponiveis
            )

    return render_template(
        'editar_oficina.html',
        oficina=oficina,
        estados=estados,
        ministrantes=ministrantes,
        clientes=clientes_disponiveis,
        eventos=eventos_disponiveis
    )

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
    # No formulário de inscrição, capture o id do tipo de inscrição escolhido:
    tipo_inscricao_id = request.form.get('tipo_inscricao_id')  # Pode ser None se for gratuita
    inscricao = Inscricao(usuario_id=current_user.id, oficina_id=oficina.id, cliente_id=current_user.cliente_id)
    inscricao.cliente_id = current_user.cliente_id
    if tipo_inscricao_id:
        inscricao.tipo_inscricao_id = tipo_inscricao_id
        # Aqui você pode chamar a função que integra com o Mercado Pago
        # Exemplo: url_pagamento = iniciar_pagamento(inscricao)
    db.session.add(inscricao)
    db.session.commit()

    try:
        # Gera o comprovante
        pdf_path = gerar_comprovante_pdf(current_user, oficina, inscricao)

        assunto = f"Confirmação de Inscrição - {oficina.titulo}"
        corpo_texto = f"Olá {current_user.nome},\n\nVocê se inscreveu na oficina '{oficina.titulo}'.\nSegue o comprovante de inscrição em anexo."

        enviar_email(
            destinatario=current_user.email,
            nome_participante=current_user.nome,
            nome_oficina=oficina.titulo,
            assunto=assunto,
            corpo_texto=corpo_texto,
            anexo_path=pdf_path
        )

        flash("Inscrição realizada! Um e-mail de confirmação foi enviado.", "success")

    except Exception as e:
        logger.error(f"❌ ERRO ao enviar e-mail: {e}", exc_info=True)
        flash("Inscrição realizada, mas houve um erro ao enviar o e-mail.", "warning")

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

    # Identificar o cliente (se houver)
    cliente = None
    if oficina.cliente_id:
        cliente = Cliente.query.get(oficina.cliente_id)

    # Se o cliente tiver fundo personalizado, use-o; senão, use o default
    if cliente and cliente.fundo_certificado:
        fundo_path = cliente.fundo_certificado
    else:
        fundo_path = "static/Certificado IAFAP.png"  # seu default atual

    # Se o cliente tiver assinatura personalizada, use-a; senão, use o default
    if cliente and cliente.assinatura_certificado:
        signature_path = cliente.assinatura_certificado
    else:
        signature_path = "static/signature.png"

    for inscrito in inscritos:
        # Tenta desenhar o fundo
        try:
            fundo = ImageReader(fundo_path)
            c.drawImage(fundo, 0, 0, width=A4[1], height=A4[0])
        except Exception as e:
            print("⚠️ Fundo do certificado não encontrado:", e)

        # Texto principal
        c.setFont("Helvetica", 16)
        texto_oficina = (
            f"{inscrito.usuario.nome}, portador do {inscrito.usuario.cpf}, participou da oficina de tema "
            f"{oficina.titulo}, com carga horária total de {oficina.carga_horaria} horas. Este certificado é "
            f"concedido como reconhecimento pela dedicação e participação no evento realizado na cidade "
            f"{oficina.cidade} nos dias:"
        )
        max_width = 600
        lines = wrap_text(texto_oficina, "Helvetica", 16, max_width, c)
        y = 340
        for line in lines:
            c.drawCentredString(420, y, line)
            y -= 25

        # Datas da oficina
        if len(oficina.dias) > 1:
            datas_formatadas = ", ".join([dia.data.strftime('%d/%m/%Y') for dia in oficina.dias[:-1]]) + \
                               " e " + oficina.dias[-1].data.strftime('%d/%m/%Y') + "."
        else:
            datas_formatadas = oficina.dias[0].data.strftime('%d/%m/%Y')
        c.drawCentredString(420, y, datas_formatadas)

        # Assinatura (personalizada ou default)
        try:
            signature_width = 360
            signature_height = 90
            x_signature = 420 - (signature_width / 2)
            y_signature = y - 187
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

    # Agora chama a função ajustada
    gerar_certificados_pdf(oficina, inscritos, pdf_path)

    flash("Certificados gerados com sucesso!", "success")
    return send_file(pdf_path, as_attachment=True)


@routes.route('/checkin/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def checkin(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)  
    
    # Descobre a que cliente pertence essa oficina
    cliente_id_oficina = oficina.cliente_id
    
    # Pega a config do cliente
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id_oficina).first()
    if not config_cliente or not config_cliente.permitir_checkin_global:
        # Caso não tenha config ou checkin não habilitado
        flash("Check-in indisponível para esta oficina!", "danger")
        return redirect(url_for('routes.dashboard_participante'))
    
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
            return redirect(url_for('routes.dashboard_participante'))
        
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
        return redirect(url_for('routes.dashboard_participante'))
    
    # Para o GET: extrai as opções configuradas (supondo que foram salvas como uma string separada por vírgulas)
    opcoes = oficina.opcoes_checkin.split(',') if oficina.opcoes_checkin else []
    return render_template('checkin.html', oficina=oficina, opcoes=opcoes)




@routes.route('/oficina/<int:oficina_id>/checkins', methods=['GET'])
@login_required
def lista_checkins(oficina_id):
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Acesso Autorizado!", "danger")
        
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
    
    # Aqui definimos a página como paisagem (landscape)
    # e colocamos margens pequenas (20 points em cada lado).
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=landscape(letter),
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20
    )
    
    elementos = []
    
    # Acessa o nome do ministrante
    ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A'
    
    elementos.append(Paragraph(f"Lista de Check-ins - {oficina.titulo}", header_style))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(f"<b>Ministrante:</b> {ministrante_nome}", normal_style))
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
    
    # Monta os dados da tabela
    data_table = [["Nome", "CPF", "E-mail", "Data e Hora do Check-in"]]
    for checkin in checkins:
        data_table.append([
            checkin.usuario.nome,
            checkin.usuario.cpf,
            checkin.usuario.email,
            checkin.data_hora.strftime("%d/%m/%Y %H:%M"),
        ])
    
    # Utiliza LongTable para quebra em múltiplas páginas e repete o cabeçalho
    # Define colWidths como ['*','*','*','*'] para usar toda a largura do doc
    tabela = LongTable(
        data_table,
        colWidths=['*','*','*','*'],  # cada coluna divide a largura disponível
        repeatRows=1  # repete o cabeçalho nas próximas páginas
    )
    
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        
        # Ativa quebra de linha em todas as células
        ('WORDWRAP', (0, 0), (-1, -1), True),
        # Ajusta o alinhamento vertical das células
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
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
        flash("Acesso Autorizado!", "danger")
        

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
        flash('Acesso Autorizado!', 'danger')
        

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

@routes.route("/toggle_checkin_global_cliente", methods=["POST"])
@login_required
def toggle_checkin_global_cliente():
    # Permite apenas clientes acessarem esta rota
    #if current_user.tipo != "cliente":
        #flash("Acesso Autorizado!", "danger")
        
        
    
    # Para clientes, já utiliza o próprio ID
    cliente_id = current_user.id

    from models import ConfiguracaoCliente
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        # Cria uma nova configuração para esse cliente, se não existir
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False
        )
        db.session.add(config_cliente)
        db.session.commit()

    # Inverte o valor de permitir_checkin_global e persiste
    config_cliente.permitir_checkin_global = not config_cliente.permitir_checkin_global
    db.session.commit()

    return jsonify({
        "success": True,
        "value": config_cliente.permitir_checkin_global,  # True ou False
        "message": "Check-in Global atualizado com sucesso!"
    })


@routes.route("/toggle_feedback_cliente", methods=["POST"])
@login_required
def toggle_feedback_cliente():
    # Permite apenas clientes
    #if current_user.tipo != "cliente":
        #flash("Acesso Autorizado!", "danger")
        
    
    cliente_id = current_user.id
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False
        )
        db.session.add(config_cliente)
        db.session.commit()

    config_cliente.habilitar_feedback = not config_cliente.habilitar_feedback
    db.session.commit()

    return jsonify({
        "success": True,
        "value": config_cliente.habilitar_feedback,
        "message": "Feedback atualizado com sucesso!"
    })


@routes.route("/toggle_certificado_cliente", methods=["POST"])
@login_required
def toggle_certificado_cliente():
    # Permite apenas clientes
    #if current_user.tipo != "cliente":
        #flash("Acesso Autorizado!", "danger")
        
    
    cliente_id = current_user.id
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False
        )
        db.session.add(config_cliente)
        db.session.commit()

    config_cliente.habilitar_certificado_individual = not config_cliente.habilitar_certificado_individual
    db.session.commit()

    return jsonify({
        "success": True,
        "value": config_cliente.habilitar_certificado_individual,
        "message": "Certificado Individual atualizado com sucesso!"
    })


@routes.route("/toggle_certificado_individual", methods=["POST"])
@login_required
def toggle_certificado_individual():
    # Permite apenas clientes (já que esta rota altera uma configuração global de certificado)
    #if current_user.tipo != "cliente":
        #flash("Acesso Autorizado!", "danger")
        
    
    config = Configuracao.query.first()
    if not config:
        config = Configuracao(
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False
        )
        db.session.add(config)
    config.habilitar_certificado_individual = not config.habilitar_certificado_individual
    db.session.commit()

    status = "ativado" if config.habilitar_certificado_individual else "desativado"
    flash(f"Certificado individual {status} com sucesso!", "success")
    return redirect(url_for("routes.dashboard_cliente"))



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
        

    # Obtendo clientes para filtro (somente admin pode visualizar)
    clientes = Cliente.query.all() if current_user.tipo == 'admin' else []

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

    # Filtros
    tipo = request.args.get('tipo')
    estrelas = request.args.get('estrelas')
    cliente_filter = request.args.get('cliente_id')

    query = Feedback.query.join(Oficina).filter(Feedback.oficina_id == oficina_id)

    # Filtra pelo tipo de feedback (usuário ou ministrante)
    if tipo == 'usuario':
        query = query.filter(Feedback.usuario_id.isnot(None))
    elif tipo == 'ministrante':
        query = query.filter(Feedback.ministrante_id.isnot(None))

    # Filtra pelo número de estrelas
    if estrelas and estrelas.isdigit():
        query = query.filter(Feedback.rating == int(estrelas))

    # Filtra pelo cliente selecionado (somente admins)
    if current_user.tipo == 'admin' and cliente_filter and cliente_filter.isdigit():
        query = query.filter(Oficina.cliente_id == int(cliente_filter))

    feedbacks = query.order_by(Feedback.created_at.desc()).all()

    
    return render_template('feedback_oficina.html', oficina=oficina, feedbacks=feedbacks,
                           total_count=total_count, total_avg=total_avg,
                           count_ministrantes=count_ministrantes, avg_ministrantes=avg_ministrantes,
                           count_usuarios=count_usuarios, avg_usuarios=avg_usuarios,  is_admin=current_user.tipo == 'admin', clientes=clientes, cliente_filter=cliente_filter)



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
from flask_login import login_required

# Configure o logger (isso pode ser configurado globalmente no seu app)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@routes.route('/cadastro_ministrante', methods=['GET', 'POST'])
def cadastro_ministrante():
    if not current_user.is_authenticated:
        # Redireciona para login ou mostra uma mensagem de que é necessário logar.
        flash('Você precisa estar logado para acessar esta página!', 'danger')
        return redirect(url_for('routes.login'))
    # Permite apenas admin e cliente
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Apenas administradores e clientes podem cadastrar ministrantes!', 'danger')
        
    
    # Se for GET, precisamos montar a lista de clientes (somente se admin)
    clientes = []
    if current_user.tipo == 'admin':
        clientes = Cliente.query.all()

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
        
        # Define o cliente_id
        if current_user.tipo == 'admin':
            # Se for admin, ele selecionou um cliente no formulário
            cliente_id = request.form.get('cliente_id')
            # Caso o admin não selecione, você pode validar, exibir erro, etc.
            # Exemplo: if not cliente_id: flash(...); return ...
        else:
            # Se for cliente, vincula automaticamente ao current_user.id
            cliente_id = current_user.id
    

        
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
            senha=generate_password_hash(senha),
            cliente_id=cliente_id  # agora usamos a variável calculada acima
        )
        
        try:
            print("Adicionando novo ministrante no banco de dados")
            db.session.add(novo_ministrante)
            db.session.commit()
            print("Ministrante cadastrado com sucesso!")
            flash('Cadastro realizado com sucesso!', 'success')
            return redirect(url_for('routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'routes.dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cadastrar ministrante: {e}", exc_info=True)
            flash('Erro ao cadastrar ministrante. Tente novamente.', 'danger')
            return redirect(url_for('routes.cadastro_ministrante'))
    
    # Se for GET, renderizamos a página. Passamos a lista de clientes se for admin.
    return render_template('cadastro_ministrante.html', clientes=clientes)


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
    ministrante = Ministrante.query.get_or_404(ministrante_id)

    # ✅ Admin pode editar todos, Cliente só edita os que cadastrou
    if current_user.tipo == 'cliente' and ministrante.cliente_id != current_user.id:
        flash('Acesso Autorizado!', 'danger')
        return redirect(url_for('routes.dashboard_cliente'))

    # Se for admin, buscamos todos os clientes para exibir no select
    # Se não for admin, pode definir `clientes = None` ou simplesmente não o usar
    if current_user.tipo == 'admin':
        clientes = Cliente.query.all()
    else:
        clientes = None

    if request.method == 'POST':
        ministrante.nome = request.form.get('nome')
        ministrante.formacao = request.form.get('formacao')
        ministrante.areas_atuacao = request.form.get('areas')
        ministrante.cpf = request.form.get('cpf')
        ministrante.pix = request.form.get('pix')
        ministrante.cidade = request.form.get('cidade')
        ministrante.estado = request.form.get('estado')
        ministrante.email = request.form.get('email')

        # Apenas admin pode trocar o cliente_id
        if current_user.tipo == 'admin':
            novo_cliente_id = request.form.get('cliente_id')
            # Se o select vier vazio, decide se mantém ou deixa 'None'
            ministrante.cliente_id = novo_cliente_id if novo_cliente_id else None

        nova_senha = request.form.get('senha')
        if nova_senha:
            ministrante.senha = generate_password_hash(nova_senha)

        db.session.commit()
        flash('Ministrante atualizado com sucesso!', 'success')
        return redirect(url_for('routes.dashboard'))

    return render_template('editar_ministrante.html',
                           ministrante=ministrante,
                           clientes=clientes)


@routes.route('/excluir_ministrante/<int:ministrante_id>', methods=['POST'])
@login_required
def excluir_ministrante(ministrante_id):
    ministrante = Ministrante.query.get_or_404(ministrante_id)

    # ✅ Admin pode excluir todos, Cliente só exclui os seus
    if current_user.tipo == 'cliente' and ministrante.cliente_id != current_user.id:
        flash('Acesso Autorizado!', 'danger')
        

    db.session.delete(ministrante)
    db.session.commit()
    flash('Ministrante excluído com sucesso!', 'success')
    return redirect(url_for('routes.gerenciar_ministrantes'))


@routes.route('/gerenciar_ministrantes', methods=['GET'])
@login_required
def gerenciar_ministrantes():
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso Autorizado!', 'danger')
        

    if current_user.tipo == 'cliente':
        ministrantes = Ministrante.query.filter_by(cliente_id=current_user.id).all()
    else:
        ministrantes = Ministrante.query.all()  # Admin vê todos

    return render_template('gerenciar_ministrantes.html', ministrantes=ministrantes)


@routes.route('/gerenciar_inscricoes', methods=['GET'])
@login_required
def gerenciar_inscricoes():
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso Autorizado!', 'danger')
        
    # Se o usuário for cliente, filtra apenas as oficinas e inscrições associadas a ele
    if current_user.tipo == 'cliente':
        oficinas = Oficina.query.filter_by(cliente_id=current_user.id).all()
        inscritos = Inscricao.query.join(Oficina).filter(Oficina.cliente_id == current_user.id).all()
    else:
        # Se for admin, mostra todos os registros
        oficinas = Oficina.query.all()
        inscritos = Inscricao.query.all()
    return render_template('gerenciar_inscricoes.html', oficinas=oficinas, inscritos=inscritos)



@routes.route('/admin_scan')
@login_required
def admin_scan():
    if current_user.tipo not in ('admin', 'cliente'):
        flash("Acesso Autorizado!", "danger")
        
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

    # 2. Define o caminho do PDF (pasta static/comprovantes, por exemplo)
    pdf_filename = "checkins_via_qr.pdf"
    pdf_path = os.path.join("static", "comprovantes", pdf_filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # 3. Configura o Documento usando SimpleDocTemplate e LongTable para quebra automática
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, PageBreak
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from collections import defaultdict

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
    title_style = styles["Title"]

    # 4. Título geral do PDF
    elements.append(Paragraph("Lista de Check-ins via QR Code", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    # 5. Agrupa os check-ins por oficina
    grupos = defaultdict(list)
    for ck in checkins_qr:
        # Caso a oficina seja None, agrupa como "N/A"
        oficina_titulo = ck.oficina.titulo if ck.oficina else "N/A"
        grupos[oficina_titulo].append(ck)

    # 6. Para cada oficina, cria uma tabela com os check-ins
    for oficina_titulo, checkins in grupos.items():
        # Cabeçalho do grupo (nome da oficina)
        elements.append(Paragraph(f"Oficina: {oficina_titulo}", styles["Heading2"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Monta os dados da tabela: cabeçalho e linhas
        table_data = [["Nome", "E-mail", "Data/Hora Check-in"]]
        for ck in checkins:
            usuario = ck.usuario
            nome = usuario.nome if usuario else ""
            email = usuario.email if usuario else ""
            data_str = ck.data_hora.strftime('%d/%m/%Y %H:%M') if ck.data_hora else ""
            table_data.append([nome, email, data_str])

        # Cria a tabela com LongTable (que permite quebra de página e repete o cabeçalho)
        table = LongTable(table_data, colWidths=[2.0 * inch, 2.5 * inch, 2.0 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('REPEATROWS', (0, 0), (-1, 0))
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5 * inch))
        # Se desejar, pode inserir uma quebra de página entre oficinas:
        # elements.append(PageBreak())

    # 7. Constrói o PDF (a quebra de página será automática se os registros ultrapassarem o limite)
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

    # Se for para filtrar pela coluna Inscricao.cliente_id:
    inscritos = Inscricao.query.filter(
        (Inscricao.cliente_id == current_user.id) | (Inscricao.cliente_id.is_(None))
    ).all()

    
    # Buscar config específica do cliente
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=current_user.id).first()
    # Se não existir, cria:
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=current_user.id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False
        )
        db.session.add(config_cliente)
        db.session.commit()

    return render_template(
        'dashboard_cliente.html',
        usuario=current_user,
        oficinas=oficinas,
        total_oficinas=total_oficinas,
        total_vagas=total_vagas,
        total_inscricoes=total_inscricoes,
        percentual_adesao=percentual_adesao,
        checkins_via_qr=checkins_via_qr,
        inscritos=inscritos,
        config_cliente=config_cliente   
    )
    
def obter_configuracao_do_cliente(cliente_id):
    config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config:
        config = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False,
        )
        db.session.add(config)
        db.session.commit()
    return config




@app.route('/oficinas_disponiveis')
@login_required
def oficinas_disponiveis():
    oficinas = Oficina.query.filter_by(cliente_id=current_user.cliente_id).all()
    return render_template('oficinas.html', oficinas=oficinas)

@routes.route('/gerar_link', methods=['GET', 'POST'])
@login_required
def gerar_link():
    if current_user.tipo not in ['cliente', 'admin']:
        return "Forbidden", 403

    cliente_id = current_user.id

    if request.method == 'POST':
        # Obtém os dados JSON da requisição
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Nenhum dado enviado'}), 400

        evento_id = data.get('evento_id')
        slug_customizado = data.get('slug_customizado')

        if not evento_id:
            return jsonify({'success': False, 'message': 'Evento não especificado'}), 400

        # Verifica se o evento pertence ao cliente
        evento = Evento.query.filter_by(id=evento_id, cliente_id=cliente_id).first()
        if not evento and current_user.tipo != 'admin':
            return jsonify({'success': False, 'message': 'Evento inválido ou não autorizado'}), 403

        # Gera um token único
        novo_token = str(uuid.uuid4())

        # Valida e limpa o slug personalizado
        if slug_customizado:
            slug_customizado = slug_customizado.strip().lower().replace(' ', '-')
            if LinkCadastro.query.filter_by(slug_customizado=slug_customizado).first():
                return jsonify({'success': False, 'message': 'Slug já está em uso'}), 400
        else:
            slug_customizado = None

        # Cria o link de cadastro no banco
        novo_link = LinkCadastro(
            cliente_id=cliente_id,
            evento_id=evento_id,
            token=novo_token,
            slug_customizado=slug_customizado
        )
        db.session.add(novo_link)
        db.session.commit()

        # Define a URL base dependendo do ambiente
        if request.host.startswith("127.0.0.1") or "localhost" in request.host:
            base_url = "http://127.0.0.1:5000"  # URL local
        else:
            base_url = "https://appfiber.com.br"  # URL de produção

        # Gera o link final
        if slug_customizado:
            link_gerado = f"{base_url}/inscricao/{slug_customizado}"
        else:
            link_gerado = f"{base_url}{url_for('routes.cadastro_participante', token=novo_token)}"

        return jsonify({'success': True, 'link': link_gerado})

    # Para GET, apenas retorna os eventos disponíveis
    eventos = Evento.query.filter_by(cliente_id=cliente_id).all()
    return jsonify({'eventos': [{'id': e.id, 'nome': e.nome} for e in eventos]})

@routes.route('/inscricao/<slug_customizado>', methods=['GET'])
def inscricao_personalizada(slug_customizado):
    # Busca o LinkCadastro pelo slug personalizado
    link = LinkCadastro.query.filter_by(slug_customizado=slug_customizado).first()
    if not link or not link.evento_id:
        return "Link inválido ou sem evento associado", 404

    # Redireciona para a rota cadastro_participante com o token
    return redirect(url_for('routes.cadastro_participante', token=link.token))


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
        habilita_pagamento = True if request.form.get('habilita_pagamento') == 'on' else False
        novo_cliente = Cliente(
            nome=request.form['nome'],
            email=request.form['email'],
            senha=request.form['senha'],
            habilita_pagamento=habilita_pagamento
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
        if nova_senha:  # Só atualiza a senha se fornecida
            cliente.senha = generate_password_hash(nova_senha)
        
        # Debug: exibe o valor recebido do checkbox
        debug_checkbox = request.form.get('habilita_pagamento')
        print("DEBUG: Valor recebido do checkbox 'habilita_pagamento':", debug_checkbox)
        # Se você tiver um logger configurado, pode usar:
        # logger.debug("Valor recebido do checkbox 'habilita_pagamento': %s", debug_checkbox)
        
        cliente.habilita_pagamento = True if debug_checkbox == 'on' else False
        
        # Debug: exibe o valor que está sendo salvo
        print("DEBUG: Valor salvo em cliente.habilita_pagamento:", cliente.habilita_pagamento)
        # logger.debug("Valor salvo em cliente.habilita_pagamento: %s", cliente.habilita_pagamento)

        try:
            db.session.commit()
            flash("Cliente atualizado com sucesso!", "success")
        except Exception as e:
            db.session.rollback()
            print("DEBUG: Erro ao atualizar cliente:", e)
            # logger.error("Erro ao atualizar cliente: %s", e, exc_info=True)
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

    # Se quiser, confira se o current_user é o dono da resposta
    if resposta.usuario_id != current_user.id:
        flash("Você não tem permissão para ver esta resposta.", "danger")
        return redirect(url_for('routes.dashboard_participante'))

    return render_template('visualizar_resposta.html', resposta=resposta)


from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

@routes.route('/formularios/<int:formulario_id>/exportar_pdf')
@login_required
def gerar_pdf_respostas(formulario_id):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet

    # Busca o formulário e as respostas
    formulario = Formulario.query.get_or_404(formulario_id)
    respostas = RespostaFormulario.query.filter_by(formulario_id=formulario.id).all()

    pdf_filename = f"respostas_{formulario.id}.pdf"
    pdf_path = f"static/{pdf_filename}"

    # Configura o documento com margens adequadas para quebra de página
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=18
    )

    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]

    elements = []
    # Título do PDF
    title = Paragraph(f"Respostas do Formulário: {formulario.nome}", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Cabeçalho da tabela
    data = []
    header = ["Usuário", "Data de Envio", "Respostas"]
    data.append(header)

    # Preenche as linhas da tabela com cada resposta
    for resposta in respostas:
        usuario = resposta.usuario.nome if resposta.usuario else "N/A"
        data_envio = resposta.data_submissao.strftime('%d/%m/%Y %H:%M')
        # Monta uma string com os campos e valores, separando-os por quebras de linha
        resposta_text = ""
        for campo in resposta.respostas_campos:
            resposta_text += f"<b>{campo.campo.nome}:</b> {campo.valor}<br/>"
        resposta_paragraph = Paragraph(resposta_text, style_normal)
        row = [usuario, data_envio, resposta_paragraph]
        data.append(row)

    # Define a largura de cada coluna (ajuste conforme necessário)
    col_widths = [150, 100, 250]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#007bff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(table)

    # Gera o PDF (o SimpleDocTemplate se encarrega da quebra de página se necessário)
    doc.build(elements)
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

@routes.route('/respostas/<path:filename>')
@login_required
def get_resposta_file(filename):
    print(">> get_resposta_file foi chamado com:", filename)
    uploads_folder = os.path.join('uploads', 'respostas')
    return send_from_directory(uploads_folder, filename)

from sqlalchemy import text  # Adicione esta importação no topo do arquivo!

from sqlalchemy import text

@routes.route('/formularios/<int:formulario_id>/excluir', methods=['POST'])
@login_required
def excluir_formulario(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)

    try:
        # 1️⃣ Exclui FeedbackCampo associados às respostas do formulário (SQL textual corrigido)
        db.session.execute(text('''
            DELETE FROM feedback_campo
            WHERE resposta_campo_id IN (
                SELECT id FROM respostas_campo
                WHERE resposta_formulario_id IN (
                    SELECT id FROM respostas_formulario
                    WHERE formulario_id = :fid
                )
            );
        '''), {'fid': formulario_id})

        # 2️⃣ Exclui RespostaCampo
        RespostaCampo.query.filter(
            RespostaCampo.resposta_formulario_id.in_(
                db.session.query(RespostaFormulario.id).filter_by(formulario_id=formulario_id)
            )
        ).delete(synchronize_session=False)

        # 3️⃣ Exclui RespostaFormulario
        RespostaFormulario.query.filter_by(formulario_id=formulario_id).delete()

        # 4️⃣ Exclui o Formulário
        formulario = Formulario.query.get_or_404(formulario_id)
        db.session.delete(formulario)

        db.session.commit()

        flash("Formulário e todos os dados relacionados excluídos com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir formulário: {str(e)}", "danger")

    return redirect(url_for('routes.listar_formularios'))

@routes.route('/upload_personalizacao_certificado', methods=['GET', 'POST'])
@login_required
def upload_personalizacao_certificado():

    if request.method == 'POST':
        logo_file = request.files.get('logo_certificado')
        fundo_file = request.files.get('fundo_certificado')
        ass_file = request.files.get('assinatura_certificado')

        # Exemplo de pasta
        pasta_uploads = os.path.join('uploads', 'personalizacao')
        os.makedirs(pasta_uploads, exist_ok=True)

        # Se o cliente enviar algo, salvamos e atualizamos o path
        if logo_file and logo_file.filename:
            filename_logo = secure_filename(logo_file.filename)
            caminho_logo = os.path.join(pasta_uploads, filename_logo)
            logo_file.save(caminho_logo)
            current_user.logo_certificado = caminho_logo  # Salva no banco

        if fundo_file and fundo_file.filename:
            filename_fundo = secure_filename(fundo_file.filename)
            caminho_fundo = os.path.join(pasta_uploads, filename_fundo)
            fundo_file.save(caminho_fundo)
            current_user.fundo_certificado = caminho_fundo

        if ass_file and ass_file.filename:
            filename_ass = secure_filename(ass_file.filename)
            caminho_ass = os.path.join(pasta_uploads, filename_ass)
            ass_file.save(caminho_ass)
            current_user.assinatura_certificado = caminho_ass

        db.session.commit()
        flash("Personalização salva com sucesso!", "success")
        return redirect(url_for('routes.dashboard_cliente'))

    return render_template('upload_personalizacao_cert.html')

@routes.route('/leitor_checkin_json', methods=['POST'])
@login_required
def leitor_checkin_json():
    """
    Esta rota faz o check-in de forma assíncrona (AJAX) e retorna JSON.
    """
    data = request.get_json()  # Lê os dados enviados em JSON
    token = data.get('token')

    if not token:
        return jsonify({"status": "error", "message": "Token não fornecido ou inválido."}), 400

    # Busca a inscrição correspondente
    inscricao = Inscricao.query.filter_by(qr_code_token=token).first()
    if not inscricao:
        return jsonify({"status": "error", "message": "Inscrição não encontrada para este token."}), 404

    # Verifica se o check-in já foi feito anteriormente
    checkin_existente = Checkin.query.filter_by(
        usuario_id=inscricao.usuario_id, 
        oficina_id=inscricao.oficina_id
    ).first()

    if checkin_existente:
        return jsonify({"status": "warning", "message": "Check-in já foi realizado!"}), 200

    # Registra o novo check-in
    novo_checkin = Checkin(
        usuario_id=inscricao.usuario_id,
        oficina_id=inscricao.oficina_id,
        palavra_chave="QR-AUTO"
    )
    db.session.add(novo_checkin)
    db.session.commit()

    # Para retornar o nome do participante e o nome da oficina,
    # basta acessar as relações: inscricao.usuario e inscricao.oficina (por exemplo)
    usuario_nome = inscricao.usuario.nome  # Ajuste conforme seu modelo
    oficina_nome = inscricao.oficina.nome  # Ajuste conforme seu modelo

    return jsonify({
        "status": "success",
        "message": "Check-in realizado com sucesso!",
        "participante": usuario_nome,
        "oficina": oficina_nome
    }), 200


@routes.route("/api/configuracao_cliente_atual", methods=["GET"])
@login_required
def configuracao_cliente_atual():
    """Retorna o estado atual das configurações do cliente logado em JSON."""
    cliente_id = current_user.id
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False
        )
        db.session.add(config_cliente)
        db.session.commit()

    return jsonify({
        "success": True,
        "permitir_checkin_global": config_cliente.permitir_checkin_global,
        "habilitar_feedback": config_cliente.habilitar_feedback,
        "habilitar_certificado_individual": config_cliente.habilitar_certificado_individual
    })
    
@routes.route('/gerar_etiquetas/<int:cliente_id>', methods=['GET'])
@login_required
def gerar_etiquetas(cliente_id):
    """Gera um PDF de etiquetas para o cliente"""
    if current_user.tipo != 'cliente' or current_user.id != cliente_id:
        flash("Acesso negado!", "danger")
        return redirect(url_for('routes.dashboard_cliente'))

    pdf_path = gerar_etiquetas_pdf(cliente_id)
    if not pdf_path:
        flash("Nenhum usuário encontrado para gerar etiquetas!", "warning")
        return redirect(url_for('routes.dashboard_cliente'))

    return send_file(pdf_path, as_attachment=True)

@routes.route('/formularios/<int:formulario_id>/respostas_ministrante', methods=['GET'])
@login_required
def listar_respostas_ministrante(formulario_id):
    # 1) Verifica se o current_user é ministrante
    if not isinstance(current_user, Ministrante):
        flash('Apenas ministrantes têm acesso a esta tela.', 'danger')
        return redirect(url_for('routes.dashboard_ministrante'))

    formulario = Formulario.query.get_or_404(formulario_id)
    # 2) Carrega as respostas
    respostas = RespostaFormulario.query.filter_by(formulario_id=formulario.id).all()

    return render_template(
        'listar_respostas_ministrante.html',
        formulario=formulario,
        respostas=respostas
    )

@routes.route('/respostas/<int:resposta_id>/feedback', methods=['GET', 'POST'])
@login_required
def dar_feedback_resposta(resposta_id):
    # Apenas ministrante pode dar feedback
    if not isinstance(current_user, Ministrante):
        flash('Apenas ministrantes podem dar feedback.', 'danger')
        return redirect(url_for('routes.dashboard_ministrante'))

    resposta = RespostaFormulario.query.get_or_404(resposta_id)

    # Exemplo: poderíamos verificar se a oficina do user bate com a do ministrante, etc.
    # if <checar se o ministrante atual tem permissão para ver esse form>

    formulario = resposta.formulario
    lista_campos = formulario.campos  # ou: CampoFormulario.query.filter_by(formulario_id=formulario.id)
    # carrega as sub-respostas (RespostaCampo) dessa resposta
    resposta_campos = resposta.respostas_campos  # gera a lista dos campos e os valores

    if request.method == 'POST':
        # Significa que o ministrante enviou feedback para 1 ou + campos
        for rcampo in resposta_campos:
            # Montar o name do textarea = "feedback_<campo.id>"
            nome_textarea = f"feedback_{rcampo.id}"
            texto_feedback = request.form.get(nome_textarea, "").strip()
            if texto_feedback:
                # criar um registro FeedbackCampo
                novo_feedback = FeedbackCampo(
                    resposta_campo_id = rcampo.id,
                    ministrante_id = current_user.id,
                    texto_feedback = texto_feedback
                )
                db.session.add(novo_feedback)
        db.session.commit()
        flash("Feedback registrado!", "success")
        return redirect(url_for('routes.dar_feedback_resposta', resposta_id=resposta_id))

    return render_template(
        'dar_feedback_resposta.html',
        resposta=resposta,
        resposta_campos=resposta_campos
    )

@routes.route('/resposta/<int:resposta_id>/definir_status', methods=['GET','POST'])
@login_required
def definir_status_resposta(resposta_id):
    # 1) Garantir que somente ministrantes possam avaliar
    if not isinstance(current_user, Ministrante):
        flash("Apenas ministrantes podem definir status de respostas.", "danger")
        return redirect(url_for('routes.dashboard_ministrante'))  

    # 2) Buscar a resposta no banco
    resposta = RespostaFormulario.query.get_or_404(resposta_id)

    # Exemplo: se quiser garantir que o ministrante só avalie respostas do seu formulário...
    # ou que pertencem a alguma oficina que ele ministra. 
    # Adapte conforme sua lógica.

    if request.method == 'POST':
        novo_status = request.form.get('status_avaliacao')
        # Exemplo: checa se o valor está na lista de escolhas
        opcoes_validas = [
            "Não Avaliada",
            "Aprovada",
            "Aprovada com ressalvas",
            "Aprovada para pôster",
            "Aprovada para apresentação oral",
            "Negada"
        ]
        if novo_status not in opcoes_validas:
            flash("Status inválido!", "danger")
            return redirect(url_for('routes.definir_status_resposta', resposta_id=resposta_id))

        # 3) Atualiza o status
        resposta.status_avaliacao = novo_status
        db.session.commit()
        flash("Status atualizado com sucesso!", "success")

        return redirect(url_for('routes.listar_respostas_ministrante', formulario_id=resposta.formulario_id))
        # ou para onde você preferir redirecionar

    # Se for GET, renderize a página com um formulário para escolher o status
    return render_template('definir_status_resposta.html', resposta=resposta)

@routes.route('/definir_status_inline', methods=['POST'])
@login_required
def definir_status_inline():
    # 1) Pega valores do form
    resposta_id = request.form.get('resposta_id')
    novo_status = request.form.get('status_avaliacao')

    # 2) Valida
    if not resposta_id or not novo_status:
        flash("Dados incompletos!", "danger")
        return redirect(request.referrer or url_for('routes.dashboard'))

    # 3) Busca a resposta no banco
    resposta = RespostaFormulario.query.get(resposta_id)
    if not resposta:
        flash("Resposta não encontrada!", "warning")
        return redirect(request.referrer or url_for('routes.dashboard'))

    # 4) Atualiza
    resposta.status_avaliacao = novo_status
    db.session.commit()

    flash("Status atualizado com sucesso!", "success")

    # Redireciona para a mesma página (listar_respostas) ou usa request.referrer
    # Se estiver em /formularios/<id>/respostas_ministrante, podemos redirecionar
    return redirect(request.referrer or url_for('routes.listar_respostas',
                                                formulario_id=resposta.formulario_id))



@routes.route('/inscrever_participantes_lote', methods=['POST'])
@login_required
def inscrever_participantes_lote():
    print("📌 [DEBUG] Iniciando processo de inscrição em lote...")

    oficina_id = request.form.get('oficina_id')
    usuario_ids = request.form.getlist('usuario_ids')

    print(f"📌 [DEBUG] Oficina selecionada: {oficina_id}")
    print(f"📌 [DEBUG] Usuários selecionados: {usuario_ids}")

    if not oficina_id or not usuario_ids:
        flash('Oficina ou participantes não selecionados corretamente.', 'warning')
        print("❌ [DEBUG] Erro: Oficina ou participantes não foram selecionados corretamente.")
        return redirect(url_for('routes.dashboard'))

    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash('Oficina não encontrada!', 'danger')
        print("❌ [DEBUG] Erro: Oficina não encontrada no banco de dados.")
        return redirect(url_for('routes.dashboard'))

    inscritos_sucesso = 0
    erros = 0

    try:
        for usuario_id in usuario_ids:
            print(f"🔄 [DEBUG] Tentando inscrever usuário {usuario_id} na oficina {oficina.titulo}...")

            ja_inscrito = Inscricao.query.filter_by(usuario_id=usuario_id, oficina_id=oficina_id).first()

            if ja_inscrito:
                print(f"⚠️ [DEBUG] Usuário {usuario_id} já está inscrito na oficina. Pulando...")
                continue  # Evita duplicação

            # Verifica se há vagas disponíveis
            if oficina.vagas <= 0:
                print(f"❌ [DEBUG] Sem vagas para a oficina {oficina.titulo}. Usuário {usuario_id} não pode ser inscrito.")
                erros += 1
                continue

            # 🔥 SOLUÇÃO: Passando cliente_id corretamente para a Inscricao
            nova_inscricao = Inscricao(
                usuario_id=usuario_id,
                oficina_id=oficina_id,
                cliente_id=oficina.cliente_id  # Obtém o cliente_id da própria oficina
            )

            db.session.add(nova_inscricao)
            oficina.vagas -= 1  # Reduz a quantidade de vagas disponíveis

            inscritos_sucesso += 1
            print(f"✅ [DEBUG] Usuário {usuario_id} inscrito com sucesso!")

        db.session.commit()
        flash(f'{inscritos_sucesso} participantes inscritos com sucesso! {erros} não foram inscritos por falta de vagas.', 'success')
        print(f"🎯 [DEBUG] {inscritos_sucesso} inscrições concluídas. {erros} falharam.")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao inscrever participantes em lote: {str(e)}", "danger")
        print(f"❌ [DEBUG] Erro ao inscrever participantes: {e}")

    return redirect(url_for('routes.dashboard'))

@routes.route('/configurar_evento', methods=['GET', 'POST'])
@login_required
def configurar_evento():
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard_cliente'))

    # Lista todos os eventos do cliente
    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    
    # Evento selecionado (por padrão, None até que o usuário escolha)
    evento_id = request.args.get('evento_id') or (request.form.get('evento_id') if request.method == 'POST' else None)
    evento = None
    if evento_id:
        evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()

    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        programacao = request.form.get('programacao')
        localizacao = request.form.get('localizacao')
        link_mapa = request.form.get('link_mapa')

        banner = request.files.get('banner')
        banner_url = evento.banner_url if evento else None
        
        if banner:
            filename = secure_filename(banner.filename)
            caminho_banner = os.path.join('static/banners', filename)
            os.makedirs(os.path.dirname(caminho_banner), exist_ok=True)
            banner.save(caminho_banner)
            banner_url = url_for('static', filename=f'banners/{filename}', _external=True)

        if evento:  # Atualizar evento existente
            evento.nome = nome
            evento.descricao = descricao
            evento.programacao = programacao
            evento.localizacao = localizacao
            evento.link_mapa = link_mapa
            if banner_url:
                evento.banner_url = banner_url
        else:  # Criar novo evento se nenhum for selecionado
            evento = Evento(
                cliente_id=current_user.id,
                nome=nome,
                descricao=descricao,
                programacao=programacao,
                localizacao=localizacao,
                link_mapa=link_mapa,
                banner_url=banner_url
            )
            db.session.add(evento)

        try:
            db.session.commit()
            flash('Evento salvo com sucesso!', 'success')
            return redirect(url_for('routes.dashboard_cliente'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar evento: {str(e)}', 'danger')

    return render_template('configurar_evento.html', eventos=eventos, evento=evento)
from collections import defaultdict
from datetime import datetime

@routes.route('/exibir_evento/<int:evento_id>')
@login_required
def exibir_evento(evento_id):
    # 1) Carrega o evento
    evento = Evento.query.get_or_404(evento_id)

    # 2) Carrega as oficinas do cliente vinculado ao evento
    #    (Aqui assumimos que evento.cliente_id é o mesmo que Oficina.cliente_id)
    oficinas = Oficina.query.filter_by(cliente_id=evento.cliente_id).all()

    # 3) Monta uma estrutura para agrupar por data
    #    grouped_oficinas[ "DD/MM/AAAA" ] = [ { 'titulo': ..., 'ministrante': ..., 'inicio': ..., 'fim': ... }, ... ]
    grouped_oficinas = defaultdict(list)

    for oficina in oficinas:
        # Cada oficina pode ter várias datas em `OficinaDia`
        for dia in oficina.dias:
            data_str = dia.data.strftime('%d/%m/%Y')
            ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A'

            grouped_oficinas[data_str].append({
                'titulo': oficina.titulo,
                'ministrante': ministrante_nome,
                'horario_inicio': dia.horario_inicio,
                'horario_fim': dia.horario_fim
            })

    # Ordena as datas no dicionário pela data real (opcional)
    # Precisamos converter a string "DD/MM/AAAA" para datetime para ordenar:
    sorted_keys = sorted(
        grouped_oficinas.keys(), 
        key=lambda d: datetime.strptime(d, '%d/%m/%Y')
    )

    # 4) Renderiza o template passando o evento e a programação agrupada
    return render_template(
        'exibir_evento.html',
        evento=evento,
        sorted_keys=sorted_keys,
        grouped_oficinas=grouped_oficinas
    )

@routes.route('/criar_evento', methods=['GET', 'POST'])
@login_required
def criar_evento():
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard_cliente'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        programacao = request.form.get('programacao')
        localizacao = request.form.get('localizacao')
        link_mapa = request.form.get('link_mapa')

        banner = request.files.get('banner')
        banner_url = None
        
        if banner:
            filename = secure_filename(banner.filename)
            caminho_banner = os.path.join('static/banners', filename)
            os.makedirs(os.path.dirname(caminho_banner), exist_ok=True)
            banner.save(caminho_banner)
            banner_url = url_for('static', filename=f'banners/{filename}', _external=True)

        novo_evento = Evento(
            cliente_id=current_user.id,
            nome=nome,
            descricao=descricao,
            programacao=programacao,
            localizacao=localizacao,
            link_mapa=link_mapa,
            banner_url=banner_url
        )
        
        try:
            db.session.add(novo_evento)
            db.session.commit()
            flash('Evento criado com sucesso!', 'success')
            return redirect(url_for('routes.dashboard_cliente'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar evento: {str(e)}', 'danger')

    return render_template('criar_evento.html')
