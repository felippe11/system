import os
from datetime import datetime
import logging
import pandas as pd
import qrcode
import requests
from flask import send_from_directory
from models import Ministrante
from flask import (Flask, Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, send_file, session)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Extensões e modelos (utilize sempre o mesmo ponto de importação para o db)
from extensions import db, login_manager
from models import (Usuario, Oficina, Inscricao, OficinaDia, Checkin,
                    Configuracao, Feedback, Ministrante, RelatorioOficina, MaterialOficina)
from utils import obter_estados, obter_cidades, gerar_qr_code, gerar_qr_code_inscricao, gerar_comprovante_pdf   # Funções auxiliares
from reportlab.lib.units import inch
from reportlab.platypus import Image




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

    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        senha = request.form.get('senha')
        formacao = request.form.get('formacao')
        # CAPTURA DOS CAMPOS DE LOCALIZAÇÃO (como array, pois são multi-select):
        estados = request.form.getlist('estados[]')
        cidades = request.form.getlist('cidades[]')
        # Junta os valores selecionados em strings separadas por vírgula:
        estados_str = ','.join(estados) if estados else ''
        cidades_str = ','.join(cidades) if cidades else ''

        print(f"📌 Recebido: Nome={nome}, CPF={cpf}, Email={email}, Formação={formacao}, Estados={estados_str}, Cidades={cidades_str}")

        # Verifica se o e-mail já existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash('Erro: Este e-mail já está cadastrado!', 'danger')
            return redirect(url_for('routes.cadastro_participante'))

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
                cidades=cidades_str
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

    return render_template('cadastro_participante.html', alert=alert)

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
    elif user_type == 'admin' or user_type == 'participante':
        return Usuario.query.get(int(user_id))
    # Caso não haja informação, tenta buscar em ambas (opcional)
    user = Usuario.query.get(int(user_id))
    if user:
        return user
    return Ministrante.query.get(int(user_id))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@routes.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        print(f"Tentativa de login para o email: {email}")
        
        # Tenta buscar primeiro em Usuario
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            print(f"Usuário encontrado na tabela Usuario: {usuario.email}, tipo: {getattr(usuario, 'tipo', 'N/A')}")
        else:
            print("Não encontrado na tabela Usuario, buscando em Ministrante...")
            usuario = Ministrante.query.filter_by(email=email).first()
            if usuario:
                print(f"Usuário encontrado na tabela Ministrante: {usuario.email}")
            else:
                print("Usuário não encontrado em nenhuma tabela.")
        
        if usuario and check_password_hash(usuario.senha, senha):
            print("Senha verificada com sucesso!")
            
            # Armazena o tipo do usuário na sessão
            if isinstance(usuario, Ministrante):
                session['user_type'] = 'ministrante'
            elif hasattr(usuario, 'tipo'):
                session['user_type'] = usuario.tipo
            else:
                session['user_type'] = 'usuario'
            
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')
            
            # Redirecionamento conforme o tipo
            if session.get('user_type') == 'admin':
                print("Redirecionando para o dashboard do Admin")
                return redirect(url_for('routes.dashboard'))
            elif session.get('user_type') == 'participante':
                print("Redirecionando para o dashboard do Participante")
                return redirect(url_for('routes.dashboard_participante'))
            elif session.get('user_type') == 'ministrante':
                print("Redirecionando para o dashboard do Ministrante")
                return redirect(url_for('routes.dashboard_ministrante'))
            else:
                print("Redirecionamento padrão para dashboard_ministrante")
                return redirect(url_for('routes.dashboard_ministrante'))
        else:
            print("Usuário não encontrado ou senha incorreta.")
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
    if current_user.tipo == 'admin':
        # Obtem os filtros (vazios se não fornecidos)
        estado_filter = request.args.get('estado', '').strip()
        cidade_filter = request.args.get('cidade', '').strip()
        
         # Obtém os check-ins que foram feitos com a palavra_chave = 'QR-AUTO'
        checkins_via_qr = Checkin.query.filter_by(palavra_chave='QR-AUTO').all()
        

        # Inicia a query e adiciona os filtros se existirem
        query = Oficina.query
        if estado_filter:
            query = query.filter(Oficina.estado == estado_filter)
        if cidade_filter:
            query = query.filter(Oficina.cidade == cidade_filter)
        oficinas = query.all()

        oficinas_com_inscritos = []
        
        # Busca os ministrantes e configurações
        ministrantes = Ministrante.query.all()
        relatorios = RelatorioOficina.query.order_by(RelatorioOficina.enviado_em.desc()).all()
        configuracao = Configuracao.query.first()
        permitir_checkin_global = configuracao.permitir_checkin_global if configuracao else False
        habilitar_feedback = configuracao.habilitar_feedback if configuracao else False
        

        # Processa as oficinas (incluindo datas e inscritos)
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

                # Acessa o ministrante via relacionamento (backref: ministrante_obj)

                'ministrante': oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A',

                'vagas': oficina.vagas,
                'carga_horaria': oficina.carga_horaria,
                'dias': dias_formatados,
                'inscritos': inscritos_info
            })
            
        return render_template('dashboard_admin.html',
                               usuario=current_user,
                               oficinas=oficinas_com_inscritos,
                               ministrantes=ministrantes,
                               relatorios=relatorios,
                               permitir_checkin_global=permitir_checkin_global,
                               habilitar_feedback=habilitar_feedback,
                               estado_filter=estado_filter,
                               cidade_filter=cidade_filter,
                               checkins_via_qr=checkins_via_qr
                               )
    
    return redirect(url_for('routes.dashboard_participante'))



@routes.route('/dashboard_participante')
@login_required
def dashboard_participante():
    if current_user.tipo != 'participante':
        return redirect(url_for('routes.dashboard'))

    # Se o participante registrou localizações, filtra as oficinas.
    if current_user.estados and current_user.cidades:
        estados = [e.strip() for e in current_user.estados.split(',') if e.strip()]
        cidades = [c.strip() for c in current_user.cidades.split(',') if c.strip()]
        oficinas = Oficina.query.filter(
            Oficina.estado.in_(estados),
            Oficina.cidade.in_(cidades)
        ).all()
    else:
        oficinas = Oficina.query.all()

    configuracao = Configuracao.query.first()
    permitir_checkin_global = configuracao.permitir_checkin_global if configuracao else False
    habilitar_feedback = configuracao.habilitar_feedback if configuracao else False

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
                           habilitar_feedback=habilitar_feedback)



# ===========================
#    GESTÃO DE OFICINAS - ADMIN
# ===========================
@routes.route('/criar_oficina', methods=['GET', 'POST'])
@login_required
def criar_oficina():
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))

    estados = obter_estados()
    # Buscar todos os ministrantes para exibir no dropdown
    todos_ministrantes = Ministrante.query.all()

    if request.method == 'POST':
        print("📌 [DEBUG] Recebendo dados do formulário...")
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        # Agora, o campo deve ser "ministrante_id" conforme o template
        ministrante_id = request.form.get('ministrante_id')
        vagas = request.form.get('vagas')
        carga_horaria = request.form.get('carga_horaria')
        estado = request.form.get('estado')
        cidade = request.form.get('cidade')

        print(f"📌 [DEBUG] Estado: {estado}")
        print(f"📌 [DEBUG] Cidade: {cidade}")
        print(f"📌 [DEBUG] Ministrante selecionado (ID): {ministrante_id}")

        if not estado or not cidade:
            flash("Erro: Estado e cidade são obrigatórios!", "danger")
            return redirect(url_for('criar_oficina'))

        # Captura múltiplas datas, horários e palavras-chave
        datas = request.form.getlist('data[]')
        horarios_inicio = request.form.getlist('horario_inicio[]')
        horarios_fim = request.form.getlist('horario_fim[]')
        palavras_chave_manha = request.form.getlist('palavra_chave_manha[]')
        palavras_chave_tarde = request.form.getlist('palavra_chave_tarde[]')

        if not datas or not horarios_inicio or not horarios_fim:
            flash('Você deve informar pelo menos uma data e horário!', 'danger')
            return redirect(url_for('criar_oficina'))

        nova_oficina = Oficina(
            titulo=titulo,
            descricao=descricao,
            ministrante_id=ministrante_id,  # Usando ministrante_id
            vagas=int(vagas),
            carga_horaria=carga_horaria,
            estado=estado,
            cidade=cidade,
        )

        print("✅ [DEBUG] Oficina criada, salvando no banco de dados...")
        db.session.add(nova_oficina)
        db.session.commit()
        print("✅ [DEBUG] Oficina salva com sucesso!")

        # Gerar o QR Code
        qr_code_path = gerar_qr_code(nova_oficina.id)
        nova_oficina.qr_code = qr_code_path
        db.session.commit()

        # Adiciona as datas da oficina
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
        
        flash('Oficina criada com sucesso!', 'success')
        return redirect(url_for('routes.dashboard'))

    return render_template('criar_oficina.html',
                           estados=estados,
                           ministrantes=todos_ministrantes,
                           datas=[],
                           horarios_inicio=[],
                           horarios_fim=[],
                           palavras_chave_manha=[],
                           palavras_chave_tarde=[])



@routes.route('/get_cidades/<estado_sigla>')
def get_cidades(estado_sigla):
    cidades = obter_cidades(estado_sigla)
    print(f"📌 Estado recebido: {estado_sigla}, Cidades encontradas: {cidades}")
    return jsonify(cidades)


@routes.route('/editar_oficina/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def editar_oficina(oficina_id):
    # Apenas admin pode editar a oficina (ou adapte para ministrantes se necessário)
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))

    estados = obter_estados()
    oficina = Oficina.query.get_or_404(oficina_id)
    # Buscar todos os ministrantes para o dropdown
    todos_ministrantes = Ministrante.query.all()

    if request.method == 'POST':
        # Atualiza os dados da oficina
        oficina.titulo = request.form.get('titulo')
        oficina.descricao = request.form.get('descricao')
        # Alteração: atualizar o vínculo com o ministrante via ministrante_id
        oficina.ministrante_id = request.form.get('ministrante_id')
        oficina.vagas = int(request.form.get('vagas'))
        oficina.carga_horaria = request.form.get('carga_horaria')
        oficina.estado = request.form.get('estado')
        oficina.cidade = request.form.get('cidade')

        # Remove os registros antigos de datas/horários
        OficinaDia.query.filter_by(oficina_id=oficina.id).delete()

        datas = request.form.getlist('data[]')
        horarios_inicio = request.form.getlist('horario_inicio[]')
        horarios_fim = request.form.getlist('horario_fim[]')
        palavras_chave_manha = request.form.getlist('palavra_chave_manha[]')
        palavras_chave_tarde = request.form.getlist('palavra_chave_tarde[]')

        for i in range(len(datas)):
            if datas[i] and horarios_inicio[i] and horarios_fim[i]:
                try:
                    data_formatada = datetime.strptime(datas[i], "%Y-%m-%d").date()
                except ValueError:
                    raise ValueError(f"Data inválida: {datas[i]}. O formato esperado é YYYY-MM-DD.")
                novo_dia = OficinaDia(
                    oficina_id=oficina.id,
                    data=data_formatada,
                    horario_inicio=horarios_inicio[i],
                    horario_fim=horarios_fim[i],
                    palavra_chave_manha=palavras_chave_manha[i],
                    palavra_chave_tarde=palavras_chave_tarde[i],
                )
                db.session.add(novo_dia)
        db.session.commit()
        flash('Oficina editada com sucesso!', 'success')
        return redirect(url_for('routes.dashboard'))

    # Preparar os dados para o template (GET)
    datas = [dia.data.strftime('%Y-%m-%d') for dia in oficina.dias]
    horarios_inicio = [dia.horario_inicio for dia in oficina.dias]
    horarios_fim = [dia.horario_fim for dia in oficina.dias]
    palavras_chave_manha = [dia.palavra_chave_manha for dia in oficina.dias]
    palavras_chave_tarde = [dia.palavra_chave_tarde for dia in oficina.dias]

    return render_template('editar_oficina.html',
                           oficina=oficina,
                           estados=estados,
                           ministrantes=todos_ministrantes,
                           datas=datas,
                           horarios_inicio=horarios_inicio,
                           horarios_fim=horarios_fim,
                           palavras_chave_manha=palavras_chave_manha,
                           palavras_chave_tarde=palavras_chave_tarde)



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

        # 1. Excluir Feedbacks relacionados à oficina
        feedbacks = Feedback.query.filter_by(oficina_id=oficina.id).all()
        for fb in feedbacks:
            db.session.delete(fb)
        db.session.commit()
        print("✅ [DEBUG] Feedbacks removidos.")

        # 2. Excluir Check-ins relacionados à oficina
        db.session.query(Checkin).filter_by(oficina_id=oficina.id).delete(synchronize_session=False)
        db.session.commit()
        print("✅ [DEBUG] Check-ins removidos.")

        # 3. Excluir Inscrições associadas à oficina
        db.session.query(Inscricao).filter_by(oficina_id=oficina.id).delete(synchronize_session=False)
        db.session.commit()
        print("✅ [DEBUG] Inscrições removidas.")

        # 4. Excluir registros de datas (OficinaDia)
        db.session.query(OficinaDia).filter_by(oficina_id=oficina.id).delete(synchronize_session=False)
        db.session.commit()
        print("✅ [DEBUG] Dias da oficina removidos.")

        # 5. Excluir Materiais associados à oficina
        materiais = MaterialOficina.query.filter_by(oficina_id=oficina.id).all()
        for material in materiais:
            db.session.delete(material)
        db.session.commit()
        print("✅ [DEBUG] Materiais da oficina removidos.")

        # 6. Excluir Relatórios associados à oficina (NOVO TRECHO)
        relatorios = RelatorioOficina.query.filter_by(oficina_id=oficina.id).all()
        for relatorio in relatorios:
            db.session.delete(relatorio)
        db.session.commit()
        print("✅ [DEBUG] Relatórios da oficina removidos.")

        # 7. Excluir a própria oficina
        db.session.delete(oficina)
        db.session.commit()
        print("✅ [DEBUG] Oficina removida com sucesso!")
        flash('Oficina excluída com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        print(f"❌ [ERRO] Erro ao excluir oficina {oficina_id}: {str(e)}")
        flash(f'Erro ao excluir oficina: {str(e)}', 'danger')

    return redirect(url_for('routes.dashboard'))



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
        return redirect(url_for('routes.dashboard'))

    oficina = Oficina.query.get(oficina_id)
    if oficina:
        oficina.vagas += 1

    db.session.delete(inscricao)
    db.session.commit()
    flash('Inscrição removida com sucesso!', 'success')
    return redirect(url_for('routes.dashboard'))


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

def gerar_certificados_pdf(oficina, inscritos, pdf_path):

    # Configurações do documento
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4))
    elements = []

    # Fundo do certificado
    fundo_path = "static/Certificado IAFAP.png"
    try:
        fundo = Image(fundo_path, width=A4[1], height=A4[0])
        elements.append(fundo)
    except Exception as e:
        print("⚠️ Fundo do certificado não encontrado:", e)

    # Conteúdo do certificado
    for inscrito in inscritos:
        elements.append(Spacer(1, 100))
        elements.append(Paragraph(inscrito.usuario.nome, styles['Title']))
        elements.append(Spacer(1, 20))

        ministrante_nome = oficina.ministrante_obj.nome if oficina.ministrante_obj else 'N/A'
        texto_oficina = f"participou da oficina {oficina.titulo}, ministrada por {ministrante_nome},"
        elements.append(Paragraph(texto_oficina, styles['Normal']))
        elements.append(Spacer(1, 10))

        texto_carga_horaria = f"com carga horária de {oficina.carga_horaria} horas, realizada nos dias:"
        elements.append(Paragraph(texto_carga_horaria, styles['Normal']))
        elements.append(Spacer(1, 10))

        if len(oficina.dias) > 1:
            datas_formatadas = ", ".join([dia.data.strftime('%d/%m/%Y') for dia in oficina.dias[:-1]]) + \
                              " e " + oficina.dias[-1].data.strftime('%d/%m/%Y') + "."
        else:
            datas_formatadas = oficina.dias[0].data.strftime('%d/%m/%Y')
        elements.append(Paragraph(datas_formatadas, styles['Normal']))
        elements.append(Spacer(1, 20))

        # Nova página para o próximo certificado
        elements.append(PageBreak())

    # Gerar o PDF
    doc.build(elements)
    
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
    pdf_path = f"static/certificados/certificados_oficina_{oficina.id}.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
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
        dia = OficinaDia.query.get(dia_id)
        if not dia:
            flash("Dia selecionado não é válido!", "danger")
            return redirect(url_for('routes.checkin', oficina_id=oficina_id))
        if dia.palavra_chave_manha and dia.palavra_chave_manha != palavra_chave_manha:
            flash("Palavra-chave da manhã está incorreta!", "danger")
            return redirect(url_for('routes.checkin', oficina_id=oficina_id))
        if palavra_chave_tarde and dia.palavra_chave_tarde and dia.palavra_chave_tarde != palavra_chave_tarde:
            flash("Palavra-chave da tarde está incorreta!", "danger")
            return redirect(url_for('routes.checkin', oficina_id=oficina_id))
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
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for("routes.dashboard"))

    try:
        oficinas = Oficina.query.all()
        if not oficinas:
            flash("Não há oficinas para excluir.", "warning")
            return redirect(url_for("routes.dashboard"))

        print(f"📌 [DEBUG] Encontradas {len(oficinas)} oficinas para exclusão.")

        qr_code_folder = os.path.join("static", "qrcodes")

        for oficina in oficinas:
            # Remover QR Code associado à oficina
            if oficina.qr_code:
                qr_code_path = os.path.join(qr_code_folder, f"checkin_{oficina.id}.png")
                if os.path.exists(qr_code_path):
                    os.remove(qr_code_path)
                    print(f"✅ [DEBUG] QR Code removido: {qr_code_path}")

        # Excluir Feedbacks relacionados às oficinas
        num_feedbacks = db.session.query(Feedback).delete()
        print(f"✅ [DEBUG] {num_feedbacks} feedbacks excluídos.")

        # Excluir Check-ins relacionados às oficinas
        num_checkins = db.session.query(Checkin).delete()
        print(f"✅ [DEBUG] {num_checkins} check-ins excluídos.")

        # Excluir Inscrições associadas às oficinas
        num_inscricoes = db.session.query(Inscricao).delete()
        print(f"✅ [DEBUG] {num_inscricoes} inscrições excluídas.")

        # Excluir Registros de Datas (OficinaDia)
        num_dias = db.session.query(OficinaDia).delete()
        print(f"✅ [DEBUG] {num_dias} registros de dias excluídos.")

        # Excluir Materiais das Oficinas
        num_materiais = db.session.query(MaterialOficina).delete()
        print(f"✅ [DEBUG] {num_materiais} materiais de oficina excluídos.")

        # Excluir Relatórios das Oficinas
        num_relatorios = db.session.query(RelatorioOficina).delete()
        print(f"✅ [DEBUG] {num_relatorios} relatórios de oficina excluídos.")

        # Excluir as Oficinas após limpar todas as referências
        num_oficinas = db.session.query(Oficina).delete()
        print(f"✅ [DEBUG] {num_oficinas} oficinas excluídas.")

        db.session.commit()
        flash(f"{num_oficinas} oficinas e todos os dados relacionados foram excluídos com sucesso!", "success")

    except Exception as e:
        db.session.rollback()
        print(f"❌ [ERRO] Erro ao excluir oficinas: {str(e)}")
        flash(f"Erro ao excluir oficinas: {str(e)}", "danger")

    return redirect(url_for("routes.dashboard"))

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
    flash(f"Check-in global {status} com sucesso!", "success")
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
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
    oficina = Oficina.query.get_or_404(oficina_id)
    feedbacks = Feedback.query.filter_by(oficina_id=oficina_id).order_by(Feedback.created_at.desc()).all()
    return render_template('feedback_oficina.html', oficina=oficina, feedbacks=feedbacks)

def gerar_pdf_feedback(oficina, feedbacks, pdf_path):
    styles = getSampleStyleSheet()
    elements = []
    title = Paragraph(f"Feedbacks da Oficina - {oficina.titulo}", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    table_data = [["Usuário", "Avaliação", "Comentário", "Data"]]
    for fb in feedbacks:
        rating_str = '★' * fb.rating + '☆' * (5 - fb.rating)
        data_str = fb.created_at.strftime('%d/%m/%Y %H:%M')
        table_data.append([fb.usuario.nome, rating_str, fb.comentario or "", data_str])
    from reportlab.platypus import Table
    table = Table(table_data, colWidths=[100, 80, 250, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#023E8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    footer = Paragraph("Feedbacks gerados em " + datetime.utcnow().strftime('%d/%m/%Y %H:%M'), styles['Normal'])
    elements.append(footer)
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    doc.build(elements)

@routes.route('/gerar_pdf_feedback/<int:oficina_id>')
@login_required
def gerar_pdf_feedback_route(oficina_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('routes.dashboard'))
    oficina = Oficina.query.get_or_404(oficina_id)
    feedbacks = Feedback.query.filter_by(oficina_id=oficina_id).order_by(Feedback.created_at.desc()).all()
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
    print(f"Foram encontradas {len(oficinas_do_ministrante)} oficinas para o ministrante {ministrante_logado.email}")

    return render_template(
        'dashboard_ministrante.html',
        ministrante=ministrante_logado,
        oficinas=oficinas_do_ministrante
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
    if current_user.tipo not in ('admin', 'staff'):
        flash("Acesso negado!", "danger")
        return redirect(url_for('routes.dashboard'))
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
        pagesize=letter,
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