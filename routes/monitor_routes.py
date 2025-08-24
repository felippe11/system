# -*- coding: utf-8 -*-
# routes/monitor_routes.py

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    make_response,
    current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import secrets
import string
import qrcode
import io
import base64
from PIL import Image
import pandas as pd

from models import Monitor, MonitorAgendamento, PresencaAluno, AgendamentoVisita, AlunoVisitante, HorarioVisitacao
from extensions import db, csrf

monitor_routes = Blueprint(
    'monitor_routes',
    __name__,
    template_folder="../templates/monitor"
)

# =======================================
# Autenticação por Código de Acesso
# =======================================
@monitor_routes.route('/monitor/login', methods=['GET', 'POST'])
@csrf.exempt
def monitor_login():
    """Login exclusivo para monitores usando código de acesso"""
    if request.method == 'POST':
        codigo_acesso = request.form.get('codigo_acesso', '').strip().upper()
        
        if not codigo_acesso:
            flash('Por favor, insira o código de acesso.', 'danger')
            return render_template('monitor/login.html')
        
        # Buscar monitor pelo código de acesso
        monitor = Monitor.query.filter_by(codigo_acesso=codigo_acesso, ativo=True).first()
        
        if not monitor:
            flash('Código de acesso inválido ou monitor inativo.', 'danger')
            return render_template('monitor/login.html')
        
        # Fazer login do monitor
        login_user(monitor)
        session['user_type'] = 'monitor'
        session['monitor_id'] = monitor.id
        
        flash(f'Bem-vindo(a), {monitor.nome_completo}!', 'success')
        return redirect(url_for('monitor_routes.dashboard'))
    
    return render_template('monitor/login.html')

@monitor_routes.route('/monitor/logout')
@login_required
def monitor_logout():
    """Logout para monitores"""
    if session.get('user_type') != 'monitor':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('auth_routes.login'))
    
    logout_user()
    session.pop('user_type', None)
    session.pop('monitor_id', None)
    flash('Logout realizado com sucesso.', 'success')
    return redirect(url_for('monitor_routes.monitor_login'))

# =======================================
# Dashboard do Monitor
# =======================================
@monitor_routes.route('/monitor/dashboard')
@login_required
def dashboard():
    """Dashboard principal do monitor"""
    if session.get('user_type') != 'monitor':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('auth_routes.login'))
    
    monitor_id = session.get('monitor_id')
    monitor = Monitor.query.get_or_404(monitor_id)
    
    # Buscar agendamentos atribuídos ao monitor para hoje
    hoje = datetime.now().date()
    agendamentos_hoje = db.session.query(AgendamentoVisita).join(
        MonitorAgendamento
    ).filter(
        MonitorAgendamento.monitor_id == monitor_id,
        MonitorAgendamento.status == 'ativo',
        db.func.date(AgendamentoVisita.data_agendamento) == hoje
    ).all()
    
    # Estatísticas do dia
    total_agendamentos = len(agendamentos_hoje)
    total_alunos = sum([ag.quantidade_alunos for ag in agendamentos_hoje])
    
    return render_template('monitor/dashboard.html', 
                         monitor=monitor,
                         agendamentos_hoje=agendamentos_hoje,
                         total_agendamentos=total_agendamentos,
                         total_alunos=total_alunos)

# =======================================
# Visualização de Agendamentos
# =======================================
@monitor_routes.route('/monitor/agendamentos')
@login_required
def listar_agendamentos():
    """Lista todos os agendamentos atribuídos ao monitor"""
    # Verificar se o usuário é admin, cliente ou monitor
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente', 'monitor']:
        if session.get('user_type') != 'monitor':
            flash('Acesso negado.', 'danger')
            return redirect(url_for('auth_routes.login'))
    
    # Se for um monitor logado via sessão, usar o monitor_id da sessão
    if session.get('user_type') == 'monitor':
        monitor_id = session.get('monitor_id')
    else:
        # Se for admin ou cliente, permitir filtrar por monitor_id via parâmetro
        monitor_id = request.args.get('monitor_id')
        if not monitor_id:
            flash('ID do monitor é obrigatório.', 'warning')
            return redirect(url_for('monitor_routes.gerenciar_monitores'))
        monitor_id = int(monitor_id)
    
    # Filtros
    data_filtro = request.args.get('data')
    status_filtro = request.args.get('status', 'todos')
    
    # Query base
    query = db.session.query(AgendamentoVisita).join(
        MonitorAgendamento
    ).filter(
        MonitorAgendamento.monitor_id == monitor_id,
        MonitorAgendamento.status == 'ativo'
    )
    
    # Aplicar filtros
    if data_filtro:
        try:
            data_obj = datetime.strptime(data_filtro, '%Y-%m-%d').date()
            query = query.filter(db.func.date(AgendamentoVisita.data_agendamento) == data_obj)
        except ValueError:
            flash('Data inválida.', 'warning')
    
    if status_filtro != 'todos':
        query = query.filter(AgendamentoVisita.status == status_filtro)
    
    agendamentos = query.order_by(AgendamentoVisita.data_agendamento.desc()).all()
    
    return render_template('monitor/agendamentos.html', 
                         agendamentos=agendamentos,
                         data_filtro=data_filtro,
                         status_filtro=status_filtro)

@monitor_routes.route('/monitor/agendamento/<int:agendamento_id>')
@login_required
def detalhe_agendamento(agendamento_id):
    """Detalhes de um agendamento específico"""
    if session.get('user_type') != 'monitor':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('auth_routes.login'))
    
    monitor_id = session.get('monitor_id')
    
    # Verificar se o agendamento está atribuído ao monitor
    monitor_agendamento = MonitorAgendamento.query.filter_by(
        monitor_id=monitor_id,
        agendamento_id=agendamento_id,
        status='ativo'
    ).first()
    
    if not monitor_agendamento:
        flash('Agendamento não encontrado ou não atribuído a você.', 'danger')
        return redirect(url_for('monitor_routes.listar_agendamentos'))
    
    agendamento = monitor_agendamento.agendamento
    alunos = agendamento.alunos
    
    # Buscar registros de presença já feitos
    registros_presenca = {}
    for aluno in alunos:
        registro = PresencaAluno.query.filter_by(
            aluno_id=aluno.id,
            monitor_id=monitor_id,
            agendamento_id=agendamento_id
        ).first()
        registros_presenca[aluno.id] = registro
    
    return render_template('monitor/detalhe_agendamento.html',
                         agendamento=agendamento,
                         alunos=alunos,
                         registros_presenca=registros_presenca)

# =======================================
# Registro de Presença
# =======================================
@monitor_routes.route('/monitor/registrar_presenca', methods=['POST'])
@login_required
def registrar_presenca():
    """Registra presença/ausência de um aluno"""
    if session.get('user_type') != 'monitor':
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    monitor_id = session.get('monitor_id')
    aluno_id = request.json.get('aluno_id')
    agendamento_id = request.json.get('agendamento_id')
    presente = request.json.get('presente', False)
    metodo = request.json.get('metodo', 'manual')
    
    try:
        # Verificar se o monitor tem acesso ao agendamento
        monitor_agendamento = MonitorAgendamento.query.filter_by(
            monitor_id=monitor_id,
            agendamento_id=agendamento_id,
            status='ativo'
        ).first()
        
        if not monitor_agendamento:
            return jsonify({'success': False, 'message': 'Agendamento não atribuído'}), 403
        
        # Verificar se o aluno pertence ao agendamento
        aluno = AlunoVisitante.query.filter_by(
            id=aluno_id,
            agendamento_id=agendamento_id
        ).first()
        
        if not aluno:
            return jsonify({'success': False, 'message': 'Aluno não encontrado'}), 404
        
        # Buscar ou criar registro de presença
        registro = PresencaAluno.query.filter_by(
            aluno_id=aluno_id,
            monitor_id=monitor_id,
            agendamento_id=agendamento_id
        ).first()
        
        if registro:
            registro.presente = presente
            registro.data_registro = datetime.utcnow()
            registro.metodo_confirmacao = metodo
        else:
            registro = PresencaAluno(
                aluno_id=aluno_id,
                monitor_id=monitor_id,
                agendamento_id=agendamento_id,
                presente=presente,
                metodo_confirmacao=metodo
            )
            db.session.add(registro)
        
        # Atualizar também o campo presente do aluno (compatibilidade)
        aluno.presente = presente
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Presença de {aluno.nome} registrada como {"presente" if presente else "ausente"}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

# =======================================
# QR Code Scanner
# =======================================
@monitor_routes.route('/monitor/qr_scanner/<int:agendamento_id>')
@login_required
def qr_scanner(agendamento_id):
    """Página do scanner de QR Code para presença"""
    if session.get('user_type') != 'monitor':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('auth_routes.login'))
    
    monitor_id = session.get('monitor_id')
    
    # Verificar acesso ao agendamento
    monitor_agendamento = MonitorAgendamento.query.filter_by(
        monitor_id=monitor_id,
        agendamento_id=agendamento_id,
        status='ativo'
    ).first()
    
    if not monitor_agendamento:
        flash('Agendamento não encontrado ou não atribuído.', 'danger')
        return redirect(url_for('monitor_routes.listar_agendamentos'))
    
    agendamento = monitor_agendamento.agendamento
    
    return render_template('monitor/qr_scanner.html', agendamento=agendamento)

@monitor_routes.route('/monitor/processar_qr', methods=['POST'])
@login_required
def processar_qr():
    """Processa QR Code lido para registrar presença"""
    if session.get('user_type') != 'monitor':
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    monitor_id = session.get('monitor_id')
    qr_token = request.json.get('qr_token')
    agendamento_id = request.json.get('agendamento_id')
    
    try:
        # Buscar agendamento pelo token QR
        agendamento = AgendamentoVisita.query.filter_by(
            qr_code_token=qr_token,
            id=agendamento_id
        ).first()
        
        if not agendamento:
            return jsonify({'success': False, 'message': 'QR Code inválido'}), 404
        
        # Verificar se o monitor tem acesso
        monitor_agendamento = MonitorAgendamento.query.filter_by(
            monitor_id=monitor_id,
            agendamento_id=agendamento_id,
            status='ativo'
        ).first()
        
        if not monitor_agendamento:
            return jsonify({'success': False, 'message': 'Acesso negado ao agendamento'}), 403
        
        # Marcar check-in do agendamento
        if not agendamento.checkin_realizado:
            agendamento.checkin_realizado = True
            agendamento.data_checkin = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Check-in realizado com sucesso!',
            'agendamento': {
                'id': agendamento.id,
                'escola_nome': agendamento.escola_nome,
                'turma': agendamento.turma,
                'quantidade_alunos': agendamento.quantidade_alunos
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

# =======================================
# Utilitários
# =======================================
def gerar_codigo_acesso():
    """Gera um código de acesso único para monitor"""
    while True:
        codigo = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        if not Monitor.query.filter_by(codigo_acesso=codigo).first():
            return codigo

@monitor_routes.route('/gerenciar-monitores')
@login_required
def gerenciar_monitores():
    """Página de gerenciamento de monitores (para admins e clientes)"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado. Apenas administradores e clientes podem acessar esta página.', 'error')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    # Filtros
    status_filter = request.args.get('status')
    curso_filter = request.args.get('curso')
    turno_filter = request.args.get('turno')
    
    # Query base
    query = Monitor.query
    
    # Aplicar filtros
    if status_filter == 'ativo':
        query = query.filter(Monitor.ativo == True)
    elif status_filter == 'inativo':
        query = query.filter(Monitor.ativo == False)
    
    if curso_filter:
        query = query.filter(Monitor.curso.ilike(f'%{curso_filter}%'))
    
    if turno_filter:
        query = query.filter(Monitor.turnos_disponibilidade.like(f'%{turno_filter}%'))
    
    monitores = query.all()
    
    # Estatísticas
    monitores_ativos = Monitor.query.filter_by(ativo=True).count()
    
    # Agendamentos de hoje
    hoje = datetime.now().date()
    agendamentos_hoje = db.session.query(AgendamentoVisita).join(
        HorarioVisitacao
    ).filter(
        HorarioVisitacao.data == hoje
    ).count()
    
    # Agendamentos cobertos (com monitor atribuído)
    agendamentos_cobertos = db.session.query(AgendamentoVisita).join(
        MonitorAgendamento
    ).join(
        HorarioVisitacao
    ).filter(
        HorarioVisitacao.data >= hoje
    ).count()
    
    # Agendamentos descobertos (sem monitor)
    agendamentos_descobertos = db.session.query(AgendamentoVisita).join(
        HorarioVisitacao
    ).filter(
        HorarioVisitacao.data >= hoje,
        ~AgendamentoVisita.id.in_(
            db.session.query(MonitorAgendamento.agendamento_id)
        )
    ).count()
    
    return render_template('monitor/gerenciar_monitores.html',
                         monitores=monitores,
                         monitores_ativos=monitores_ativos,
                         agendamentos_hoje=agendamentos_hoje,
                         agendamentos_cobertos=agendamentos_cobertos,
                         agendamentos_descobertos=agendamentos_descobertos,
                         today=hoje)

@monitor_routes.route('/novo-monitor')
@login_required
def novo_monitor():
    """Página para cadastrar novo monitor"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado. Apenas administradores e clientes podem acessar esta página.', 'error')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    return render_template('monitor/novo_monitor.html')

@monitor_routes.route('/cadastrar-monitor', methods=['POST'])
@login_required
def cadastrar_monitor():
    """Cadastra um novo monitor"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    try:
        # Obter dados do formulário
        nome_completo = request.form.get('nome_completo')
        curso = request.form.get('curso')
        email = request.form.get('email')
        telefone_whatsapp = request.form.get('telefone_whatsapp')
        carga_horaria = int(request.form.get('carga_horaria_disponibilidade'))
        
        # Obter dias e turnos de disponibilidade
        dias_disponibilidade = request.form.getlist('dias_disponibilidade')
        turnos_disponibilidade = request.form.getlist('turnos_disponibilidade')
        
        # Validações
        if not all([nome_completo, curso, email, telefone_whatsapp]):
            flash('Todos os campos obrigatórios devem ser preenchidos.', 'error')
            return redirect(url_for('monitor_routes.gerenciar_monitores'))
        
        if not dias_disponibilidade:
            flash('Selecione pelo menos um dia de disponibilidade.', 'error')
            return redirect(url_for('monitor_routes.gerenciar_monitores'))
        
        if not turnos_disponibilidade:
            flash('Selecione pelo menos um turno de disponibilidade.', 'error')
            return redirect(url_for('monitor_routes.gerenciar_monitores'))
        
        # Verificar se o email já existe
        if Monitor.query.filter_by(email=email).first():
            flash('Já existe um monitor cadastrado com este email.', 'error')
            return redirect(url_for('monitor_routes.gerenciar_monitores'))
        
        # Criar novo monitor
        monitor = Monitor(
            nome_completo=nome_completo,
            curso=curso,
            email=email,
            telefone_whatsapp=telefone_whatsapp,
            carga_horaria_disponibilidade=carga_horaria,
            dias_disponibilidade=','.join(dias_disponibilidade),
            turnos_disponibilidade=','.join(turnos_disponibilidade),
            codigo_acesso=gerar_codigo_acesso(),
            ativo=True
        )
        
        db.session.add(monitor)
        db.session.commit()
        
        flash(f'Monitor {nome_completo} cadastrado com sucesso! Código de acesso: {monitor.codigo_acesso}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao cadastrar monitor: {str(e)}', 'error')
    
    return redirect(url_for('monitor_routes.gerenciar_monitores'))

@monitor_routes.route('/monitor/toggle-status/<int:monitor_id>', methods=['POST'])
@login_required
def toggle_status_monitor_route(monitor_id):
    """Alterna o status ativo/inativo de um monitor (rota para monitores)"""
    return toggle_status_monitor(monitor_id)

@monitor_routes.route('/toggle-status/<int:monitor_id>', methods=['POST'])
@login_required
def toggle_status_monitor(monitor_id):
    """Alterna o status ativo/inativo de um monitor"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        monitor = Monitor.query.get_or_404(monitor_id)
        monitor.ativo = not monitor.ativo
        db.session.commit()
        
        status = 'ativado' if monitor.ativo else 'desativado'
        return jsonify({'success': True, 'message': f'Monitor {status} com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@monitor_routes.route('/excluir/<int:monitor_id>', methods=['DELETE'])
@login_required
def excluir_monitor(monitor_id):
    """Exclui um monitor"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        monitor = Monitor.query.get_or_404(monitor_id)
        
        # Verificar se o monitor tem agendamentos atribuídos
        agendamentos_atribuidos = MonitorAgendamento.query.filter_by(monitor_id=monitor_id).count()
        if agendamentos_atribuidos > 0:
            return jsonify({
                'success': False, 
                'message': f'Não é possível excluir. Monitor possui {agendamentos_atribuidos} agendamentos atribuídos.'
            })
        
        db.session.delete(monitor)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Monitor excluído com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@monitor_routes.route('/monitor/editar/<int:monitor_id>')
@login_required
def editar_monitor_route(monitor_id):
    """Página de edição de monitor (rota para monitores)"""
    return editar_monitor(monitor_id)

@monitor_routes.route('/editar/<int:monitor_id>')
@login_required
def editar_monitor(monitor_id):
    """Página de edição de monitor com visualização de agendamentos"""
    # Verificar se o usuário é admin ou cliente
    user_type = getattr(current_user, 'tipo', None)
    session_type = session.get('user_type')
    if user_type not in ['admin', 'cliente'] and session_type not in ['admin', 'cliente']:
        flash('Acesso negado', 'error')
        return redirect(url_for('monitor_routes.gerenciar_monitores'))
    
    try:
        monitor = Monitor.query.get_or_404(monitor_id)
        
        # Buscar agendamentos associados ao monitor
        agendamentos = db.session.query(
            MonitorAgendamento,
            AgendamentoVisita,
            HorarioVisitacao
        ).join(
            AgendamentoVisita, MonitorAgendamento.agendamento_id == AgendamentoVisita.id
        ).join(
            HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
        ).filter(
            MonitorAgendamento.monitor_id == monitor_id
        ).order_by(HorarioVisitacao.data.desc()).all()
        
        # Estatísticas do monitor
        total_agendamentos = len(agendamentos)
        agendamentos_hoje = sum(
            1 for ma, av, hv in agendamentos if hv.data == datetime.now().date()
        )
        agendamentos_futuros = sum(
            1 for ma, av, hv in agendamentos if hv.data > datetime.now().date()
        )
        
        return render_template('editar_monitor.html', 
                             monitor=monitor,
                             agendamentos=agendamentos,
                             total_agendamentos=total_agendamentos,
                             agendamentos_hoje=agendamentos_hoje,
                             agendamentos_futuros=agendamentos_futuros)
        
    except Exception as e:
        flash(f'Erro ao carregar dados do monitor: {str(e)}', 'error')
        return redirect(url_for('monitor_routes.gerenciar_monitores'))

@monitor_routes.route('/atualizar/<int:monitor_id>', methods=['POST'])
@login_required
def atualizar_monitor(monitor_id):
    """Atualiza os dados de um monitor"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        monitor = Monitor.query.get_or_404(monitor_id)
        
        # Atualizar dados básicos
        monitor.nome_completo = request.form.get('nome_completo')
        monitor.curso = request.form.get('curso')
        monitor.email = request.form.get('email')
        monitor.telefone_whatsapp = request.form.get('telefone_whatsapp')
        monitor.carga_horaria_disponibilidade = int(request.form.get('carga_horaria_disponibilidade', 0))
        
        # Atualizar disponibilidade
        dias_selecionados = request.form.getlist('dias_disponibilidade')
        turnos_selecionados = request.form.getlist('turnos_disponibilidade')
        
        monitor.dias_disponibilidade = ','.join(dias_selecionados)
        monitor.turnos_disponibilidade = ','.join(turnos_selecionados)
        
        db.session.commit()
        
        flash('Monitor atualizado com sucesso!', 'success')
        return redirect(url_for('monitor_routes.editar_monitor', monitor_id=monitor_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar monitor: {str(e)}', 'error')
        return redirect(url_for('monitor_routes.editar_monitor', monitor_id=monitor_id))

@monitor_routes.route('/distribuicao-manual')
@login_required
def distribuicao_manual():
    """Página para distribuição manual de monitores por agendamento"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Buscar agendamentos sem monitor atribuído
        agendamentos_sem_monitor = db.session.query(
            AgendamentoVisita,
            HorarioVisitacao
        ).join(
            HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
        ).outerjoin(
            MonitorAgendamento, AgendamentoVisita.id == MonitorAgendamento.agendamento_id
        ).filter(
            MonitorAgendamento.id.is_(None),
            HorarioVisitacao.data >= datetime.now().date()
        ).order_by(HorarioVisitacao.data, HorarioVisitacao.horario_inicio).all()
        
        # Buscar monitores ativos
        monitores_ativos = Monitor.query.filter_by(ativo=True).order_by(Monitor.nome_completo).all()
        
        # Buscar agendamentos já atribuídos (para referência)
        agendamentos_atribuidos = db.session.query(
            MonitorAgendamento,
            AgendamentoVisita,
            HorarioVisitacao,
            Monitor
        ).join(
            AgendamentoVisita, MonitorAgendamento.agendamento_id == AgendamentoVisita.id
        ).join(
            HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
        ).join(
            Monitor, MonitorAgendamento.monitor_id == Monitor.id
        ).filter(
            HorarioVisitacao.data >= datetime.now().date()
        ).order_by(HorarioVisitacao.data, HorarioVisitacao.horario_inicio).all()
        
        return render_template('distribuicao_manual.html',
                             agendamentos_sem_monitor=agendamentos_sem_monitor,
                             monitores_ativos=monitores_ativos,
                             agendamentos_atribuidos=agendamentos_atribuidos)
        
    except Exception as e:
        flash(f'Erro ao carregar dados: {str(e)}', 'error')
        return redirect(url_for('monitor_routes.gerenciar_monitores'))

@monitor_routes.route('/atribuir-monitor', methods=['POST'])
@login_required
def atribuir_monitor():
    """Atribui um monitor a um agendamento específico"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        agendamento_id = request.form.get('agendamento_id')
        monitor_id = request.form.get('monitor_id')
        
        if not agendamento_id or not monitor_id:
            return jsonify({'success': False, 'message': 'Dados incompletos'})
        
        # Verificar se o agendamento existe e não tem monitor
        agendamento = AgendamentoVisita.query.get_or_404(agendamento_id)
        monitor_existente = MonitorAgendamento.query.filter_by(agendamento_id=agendamento_id).first()
        
        if monitor_existente:
            return jsonify({'success': False, 'message': 'Agendamento já possui monitor atribuído'})
        
        # Verificar se o monitor existe e está ativo
        monitor = Monitor.query.get_or_404(monitor_id)
        if not monitor.ativo:
            return jsonify({'success': False, 'message': 'Monitor não está ativo'})
        
        # Criar a atribuição
        nova_atribuicao = MonitorAgendamento(
            monitor_id=monitor_id,
            agendamento_id=agendamento_id,
            data_atribuicao=datetime.now()
        )
        
        db.session.add(nova_atribuicao)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Monitor {monitor.nome_completo} atribuído com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@monitor_routes.route('/remover-atribuicao', methods=['POST'])
@login_required
def remover_atribuicao():
    """Remove a atribuição de um monitor de um agendamento"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        agendamento_id = request.form.get('agendamento_id')
        
        if not agendamento_id:
            return jsonify({'success': False, 'message': 'ID do agendamento não fornecido'})
        
        # Buscar e remover a atribuição
        atribuicao = MonitorAgendamento.query.filter_by(agendamento_id=agendamento_id).first()
        
        if not atribuicao:
            return jsonify({'success': False, 'message': 'Atribuição não encontrada'})
        
        db.session.delete(atribuicao)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Atribuição removida com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@monitor_routes.route('/importacao-massa')
@login_required
def importacao_massa():
    """Página para importação em massa de monitores"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('importacao_massa.html')

@monitor_routes.route('/processar-importacao', methods=['POST'])
@login_required
def processar_importacao():
    """Processa a importação em massa de monitores"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        # Verificar se foi enviado um arquivo
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo foi enviado'})
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})
        
        # Verificar extensão do arquivo
        extensoes_permitidas = ['.xlsx', '.xls', '.csv']
        extensao = arquivo.filename.lower().split('.')[-1]
        if f'.{extensao}' not in extensoes_permitidas:
            return jsonify({
                'success': False, 
                'message': 'Formato de arquivo não suportado. Use XLSX, XLS ou CSV.'
            })
        
        # Processar arquivo baseado na extensão
        monitores_dados = []
        
        if extensao in ['xlsx', 'xls']:
            # Processar arquivo Excel
            import pandas as pd
            df = pd.read_excel(arquivo)
            monitores_dados = df.to_dict('records')
        
        elif extensao == 'csv':
            # Processar arquivo CSV
            import pandas as pd
            df = pd.read_csv(arquivo)
            monitores_dados = df.to_dict('records')
        
        # Validar e processar dados
        monitores_criados = 0
        erros = []
        
        for i, dados in enumerate(monitores_dados, 1):
            try:
                # Validar campos obrigatórios
                campos_obrigatorios = ['nome_completo', 'curso', 'email', 'telefone_whatsapp', 
                                     'carga_horaria_disponibilidade', 'dias_disponibilidade', 
                                     'turnos_disponibilidade']
                
                for campo in campos_obrigatorios:
                    if campo not in dados or pd.isna(dados[campo]) or str(dados[campo]).strip() == '':
                        raise ValueError(f'Campo obrigatório "{campo}" não preenchido')
                
                # Verificar se o email já existe
                monitor_existente = Monitor.query.filter_by(email=dados['email']).first()
                if monitor_existente:
                    raise ValueError(f'Email {dados["email"]} já está cadastrado')
                
                # Criar novo monitor
                novo_monitor = Monitor(
                    nome_completo=str(dados['nome_completo']).strip(),
                    curso=str(dados['curso']).strip(),
                    email=str(dados['email']).strip().lower(),
                    telefone_whatsapp=str(dados['telefone_whatsapp']).strip(),
                    carga_horaria_disponibilidade=int(dados['carga_horaria_disponibilidade']),
                    dias_disponibilidade=str(dados['dias_disponibilidade']).strip(),
                    turnos_disponibilidade=str(dados['turnos_disponibilidade']).strip(),
                    codigo_acesso=gerar_codigo_acesso(),
                    ativo=True
                )
                
                db.session.add(novo_monitor)
                monitores_criados += 1
                
            except Exception as e:
                erros.append(f'Linha {i}: {str(e)}')
                continue
        
        # Salvar no banco de dados
        if monitores_criados > 0:
            db.session.commit()
        
        # Preparar resposta
        mensagem = f'{monitores_criados} monitores importados com sucesso.'
        if erros:
            mensagem += f' {len(erros)} erros encontrados.'
        
        return jsonify({
            'success': True,
            'message': mensagem,
            'monitores_criados': monitores_criados,
            'erros': erros[:10]  # Limitar a 10 erros para não sobrecarregar
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao processar arquivo: {str(e)}'})

@monitor_routes.route('/download-template')
@login_required
def download_template():
    """Download do template para importação em massa"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado', 'error')
        return redirect(url_for('main.index'))
    
    try:
        import pandas as pd
        from flask import make_response
        
        # Criar dados de exemplo para o template
        dados_exemplo = {
            'nome_completo': ['João Silva Santos', 'Maria Oliveira Costa'],
            'curso': ['Medicina', 'Enfermagem'],
            'email': ['joao.silva@email.com', 'maria.oliveira@email.com'],
            'telefone_whatsapp': ['(11) 99999-9999', '(11) 88888-8888'],
            'carga_horaria_disponibilidade': [20, 15],
            'dias_disponibilidade': ['Segunda,Terça,Quarta', 'Quinta,Sexta,Sábado'],
            'turnos_disponibilidade': ['Manhã,Tarde', 'Tarde,Noite']
        }
        
        df = pd.DataFrame(dados_exemplo)
        
        # Criar resposta com arquivo Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Monitores', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=template_monitores.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao gerar template: {str(e)}', 'error')
        return redirect(url_for('monitor_routes.importacao_massa'))

@monitor_routes.route('/cadastro-multiplo')
@login_required
def cadastro_multiplo():
    """Página para cadastro simultâneo de múltiplos monitores"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('cadastro_multiplo.html')

@monitor_routes.route('/processar-cadastro-multiplo', methods=['POST'])
@login_required
def processar_cadastro_multiplo():
    """Processa o cadastro simultâneo de múltiplos monitores"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        # Obter dados do formulário
        monitores_data = request.get_json()
        
        if not monitores_data or 'monitores' not in monitores_data:
            return jsonify({'success': False, 'message': 'Dados inválidos'})
        
        monitores_criados = 0
        erros = []
        
        for i, dados in enumerate(monitores_data['monitores'], 1):
            try:
                # Validar campos obrigatórios
                campos_obrigatorios = ['nome_completo', 'curso', 'email', 'telefone_whatsapp', 
                                     'carga_horaria_disponibilidade']
                
                for campo in campos_obrigatorios:
                    if not dados.get(campo) or str(dados[campo]).strip() == '':
                        raise ValueError(f'Campo obrigatório "{campo}" não preenchido')
                
                # Verificar se o email já existe
                monitor_existente = Monitor.query.filter_by(email=dados['email']).first()
                if monitor_existente:
                    raise ValueError(f'Email {dados["email"]} já está cadastrado')
                
                # Processar dias de disponibilidade
                dias_selecionados = dados.get('dias_disponibilidade', [])
                if not dias_selecionados:
                    raise ValueError('Pelo menos um dia de disponibilidade deve ser selecionado')
                
                dias_disponibilidade = ','.join(dias_selecionados)
                
                # Processar turnos de disponibilidade
                turnos_selecionados = dados.get('turnos_disponibilidade', [])
                if not turnos_selecionados:
                    raise ValueError('Pelo menos um turno de disponibilidade deve ser selecionado')
                
                turnos_disponibilidade = ','.join(turnos_selecionados)
                
                # Criar novo monitor
                novo_monitor = Monitor(
                    nome_completo=str(dados['nome_completo']).strip(),
                    curso=str(dados['curso']).strip(),
                    email=str(dados['email']).strip().lower(),
                    telefone_whatsapp=str(dados['telefone_whatsapp']).strip(),
                    carga_horaria_disponibilidade=int(dados['carga_horaria_disponibilidade']),
                    dias_disponibilidade=dias_disponibilidade,
                    turnos_disponibilidade=turnos_disponibilidade,
                    codigo_acesso=gerar_codigo_acesso(),
                    ativo=True
                )
                
                db.session.add(novo_monitor)
                monitores_criados += 1
                
            except Exception as e:
                erros.append(f'Monitor {i}: {str(e)}')
                continue
        
        # Salvar no banco de dados
        if monitores_criados > 0:
            db.session.commit()
        
        # Preparar resposta
        mensagem = f'{monitores_criados} monitores cadastrados com sucesso.'
        if erros:
            mensagem += f' {len(erros)} erros encontrados.'
        
        return jsonify({
            'success': True,
            'message': mensagem,
            'monitores_criados': monitores_criados,
            'erros': erros
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao processar cadastros: {str(e)}'})

@monitor_routes.route('/monitor/excluir/<int:monitor_id>', methods=['DELETE'])
@login_required
def excluir_monitor_route(monitor_id):
    """Wrapper para excluir_monitor com prefixo /monitor/"""
    return excluir_monitor(monitor_id)

@monitor_routes.route('/monitor/atribuir-monitor', methods=['POST'])
@login_required
def atribuir_monitor_route():
    """Wrapper para atribuir_monitor com prefixo /monitor/"""
    return atribuir_monitor()

@monitor_routes.route('/monitor/remover-atribuicao', methods=['POST'])
@login_required
def remover_atribuicao_route():
    """Wrapper para remover_atribuicao com prefixo /monitor/"""
    return remover_atribuicao()

@monitor_routes.route('/distribuicao-automatica')
@login_required
def distribuicao_automatica():
    """Página de distribuição automática de monitores"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    # Obter estatísticas para exibir na página
    hoje = datetime.now().date()
    agendamentos_sem_monitor = db.session.query(AgendamentoVisita).join(
        HorarioVisitacao
    ).filter(
        HorarioVisitacao.data >= hoje,
        AgendamentoVisita.status == 'confirmado',
        ~AgendamentoVisita.id.in_(
            db.session.query(MonitorAgendamento.agendamento_id)
        )
    ).count()
    
    monitores_ativos = Monitor.query.filter_by(ativo=True).count()
    
    return render_template('monitor/distribuicao_automatica.html',
                         agendamentos_sem_monitor=agendamentos_sem_monitor,
                         monitores_ativos=monitores_ativos)

@monitor_routes.route('/monitor/distribuir-automaticamente', methods=['POST'])
@login_required
def distribuir_automaticamente_monitor():
    """Executa a distribuição automática de monitores (rota para monitores)"""
    return distribuir_automaticamente()

@monitor_routes.route('/distribuir-automaticamente', methods=['POST'])
@login_required
def distribuir_automaticamente():
    """Executa a distribuição automática de monitores"""
    # Verificar se o usuário é admin ou cliente
    if not hasattr(current_user, 'tipo') or current_user.tipo not in ['admin', 'cliente']:
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        # Obter agendamentos futuros sem monitor atribuído
        hoje = datetime.now().date()
        current_app.logger.info(
            "Iniciando distribuição automática de monitores"
        )
        agendamentos_sem_monitor = db.session.query(AgendamentoVisita).join(
            HorarioVisitacao
        ).filter(
            HorarioVisitacao.data >= hoje,
            AgendamentoVisita.status.in_(['confirmado', 'pendente']),
            ~AgendamentoVisita.id.in_(
                db.session.query(MonitorAgendamento.agendamento_id)
            )
        ).order_by(
            HorarioVisitacao.data,
            HorarioVisitacao.horario_inicio,
        ).all()
        
        # Obter monitores ativos
        monitores_ativos = Monitor.query.filter_by(ativo=True).all()
        
        if not monitores_ativos:
            current_app.logger.warning("Nenhum monitor ativo encontrado")
            return jsonify({
                'success': False,
                'message': 'Nenhum monitor ativo encontrado',
            })
        
        atribuicoes_realizadas = 0
        
        for agendamento in agendamentos_sem_monitor:
            # Determinar o turno do agendamento
            hora_inicio = agendamento.horario.horario_inicio.hour
            if hora_inicio < 12:
                turno_agendamento = 'manha'
            elif hora_inicio < 18:
                turno_agendamento = 'tarde'
            else:
                turno_agendamento = 'noite'
            
            # Determinar o dia da semana
            dias_semana = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo']
            dia_agendamento = dias_semana[agendamento.horario.data.weekday()]
            
            # Encontrar monitores disponíveis para este agendamento
            monitores_disponiveis = []
            for monitor in monitores_ativos:
                # Verificar disponibilidade de dia
                if dia_agendamento in monitor.get_dias_disponibilidade():
                    # Verificar disponibilidade de turno
                    if turno_agendamento in monitor.get_turnos_disponibilidade():
                        # Verificar carga horária (simplificado)
                        agendamentos_monitor = MonitorAgendamento.query.filter_by(
                            monitor_id=monitor.id
                        ).count()
                        
                        # Assumindo 4 horas por agendamento em média
                        horas_utilizadas = agendamentos_monitor * 4
                        if horas_utilizadas < monitor.carga_horaria_disponibilidade:
                            monitores_disponiveis.append(monitor)
            
            # Atribuir ao monitor com menor carga atual
            if monitores_disponiveis:
                monitor_escolhido = min(
                    monitores_disponiveis,
                    key=lambda m: MonitorAgendamento.query.filter_by(
                        monitor_id=m.id
                    ).count(),
                )

                # Criar atribuição
                atribuicao = MonitorAgendamento(
                    monitor_id=monitor_escolhido.id,
                    agendamento_id=agendamento.id,
                    data_atribuicao=datetime.now(),
                    tipo_distribuicao='automatica',
                    status='ativo',
                )

                db.session.add(atribuicao)
                atribuicoes_realizadas += 1
                current_app.logger.info(
                    "Monitor %s atribuído ao agendamento %s",
                    monitor_escolhido.id,
                    agendamento.id,
                )
            else:
                current_app.logger.warning(
                    "Nenhum monitor disponível para o agendamento %s",
                    agendamento.id,
                )

        if atribuicoes_realizadas == 0:
            current_app.logger.warning(
                "Nenhuma atribuição de monitor foi realizada"
            )
            return jsonify({
                'success': False,
                'message': 'Nenhuma atribuição realizada',
                'atribuicoes': 0,
            })

        db.session.commit()
        current_app.logger.info(
            "Distribuição automática concluída com %s atribuições",
            atribuicoes_realizadas,
        )

        return jsonify({
            'success': True,
            'message': 'Distribuição automática concluída',
            'atribuicoes': atribuicoes_realizadas,
        })
         
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@monitor_routes.route('/gerar-qrcode/<int:agendamento_id>')
@login_required
def gerar_qrcode(agendamento_id):
    """Gera QR Code para um agendamento específico"""
    # Verificar se o usuário é monitor, admin ou cliente
    if not (hasattr(current_user, 'codigo_acesso') or 
            (hasattr(current_user, 'tipo') and current_user.tipo in ['admin', 'cliente'])):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        agendamento = AgendamentoVisita.query.get_or_404(agendamento_id)
        
        # Se for monitor, verificar se está atribuído a este agendamento
        if hasattr(current_user, 'codigo_acesso'):
            atribuicao = MonitorAgendamento.query.filter_by(
                monitor_id=current_user.id,
                agendamento_id=agendamento_id
            ).first()
            if not atribuicao:
                return jsonify({'success': False, 'message': 'Agendamento não atribuído a você'})
        
        # Dados para o QR Code
        qr_data = {
            'agendamento_id': agendamento_id,
            'timestamp': datetime.now().isoformat(),
            'type': 'presenca_agendamento'
        }
        
        # Criar QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(qr_data))
        qr.make(fit=True)
        
        # Gerar imagem
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'qr_code': f'data:image/png;base64,{img_base64}',
            'agendamento_id': agendamento_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@monitor_routes.route('/processar-qrcode', methods=['POST'])
@login_required
def processar_qrcode():
    """Processa a leitura de QR Code para confirmação de presença"""
    # Verificar se o usuário é monitor
    if not hasattr(current_user, 'codigo_acesso'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        data = request.get_json()
        qr_data = data.get('qr_data')
        aluno_id = data.get('aluno_id')
        agendamento_id = data.get('agendamento_id')
        
        if not all([qr_data, aluno_id, agendamento_id]):
            return jsonify({'success': False, 'message': 'Dados incompletos'})
        
        # Verificar se o monitor está atribuído a este agendamento
        atribuicao = MonitorAgendamento.query.filter_by(
            monitor_id=current_user.id,
            agendamento_id=agendamento_id
        ).first()
        
        if not atribuicao:
            return jsonify({'success': False, 'message': 'Agendamento não atribuído a você'})
        
        # Verificar se o aluno existe
        aluno = AlunoVisitante.query.get(aluno_id)
        if not aluno:
            return jsonify({'success': False, 'message': 'Aluno não encontrado'})
        
        # Verificar se já existe registro de presença
        presenca_existente = PresencaAluno.query.filter_by(
            aluno_id=aluno_id,
            agendamento_id=agendamento_id
        ).first()
        
        if presenca_existente:
            # Atualizar registro existente
            presenca_existente.presente = True
            presenca_existente.data_registro = datetime.now()
            presenca_existente.metodo_confirmacao = 'qrcode'
            presenca_existente.monitor_id = current_user.id
        else:
            # Criar novo registro
            presenca = PresencaAluno(
                aluno_id=aluno_id,
                monitor_id=current_user.id,
                agendamento_id=agendamento_id,
                presente=True,
                data_registro=datetime.now(),
                metodo_confirmacao='qrcode'
            )
            db.session.add(presenca)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Presença de {aluno.nome} confirmada via QR Code',
            'aluno_nome': aluno.nome
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@monitor_routes.route('/gerar-qrcode-aluno/<int:aluno_id>/<int:agendamento_id>')
@login_required
def gerar_qrcode_aluno(aluno_id, agendamento_id):
    """Gera QR Code específico para um aluno em um agendamento"""
    # Verificar se o usuário é monitor ou admin
    if not (hasattr(current_user, 'codigo_acesso') or 
            (hasattr(current_user, 'tipo') and current_user.tipo == 'admin')):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        aluno = AlunoVisitante.query.get_or_404(aluno_id)
        agendamento = AgendamentoVisita.query.get_or_404(agendamento_id)
        
        # Se for monitor, verificar se está atribuído a este agendamento
        if hasattr(current_user, 'codigo_acesso'):
            atribuicao = MonitorAgendamento.query.filter_by(
                monitor_id=current_user.id,
                agendamento_id=agendamento_id
            ).first()
            if not atribuicao:
                return jsonify({'success': False, 'message': 'Agendamento não atribuído a você'})
        
        # Dados para o QR Code
        qr_data = {
            'aluno_id': aluno_id,
            'agendamento_id': agendamento_id,
            'timestamp': datetime.now().isoformat(),
            'type': 'presenca_aluno'
        }
        
        # Criar QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=2,
        )
        qr.add_data(str(qr_data))
        qr.make(fit=True)
        
        # Gerar imagem
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'qr_code': f'data:image/png;base64,{img_base64}',
            'aluno_nome': aluno.nome,
            'agendamento_id': agendamento_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})