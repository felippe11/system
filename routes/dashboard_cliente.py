from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from extensions import db
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from models import (
    Evento, Oficina, Inscricao, Checkin,
    ConfiguracaoCliente, AgendamentoVisita, HorarioVisitacao, Usuario
)

# Importa o blueprint central para registrar as rotas deste módulo
from .dashboard_routes import dashboard_routes

@dashboard_routes.route('/dashboard_cliente')
@login_required
def dashboard_cliente():
    if current_user.tipo != 'cliente':
        return redirect(url_for('dashboard_routes.dashboard'))

    print(f"📌 [DEBUG] Cliente autenticado: {current_user.email} (ID: {current_user.id})")
    print("Usuário logado:", current_user.email)
    print("ID:", current_user.id)
    print("Tipo:", current_user.tipo if hasattr(current_user, 'tipo') else "N/A")


    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    print("✅ Eventos:", eventos)
  
    

    # Mostra apenas as oficinas criadas por este cliente OU pelo admin (cliente_id nulo)
    oficinas = Oficina.query.filter_by(cliente_id=current_user.id).all()

    # Cálculo das estatísticas
    total_oficinas = len(oficinas)
    
    # Novo cálculo do total_vagas conforme solicitado:
    # 1. Soma as vagas das oficinas com tipo_inscricao 'com_inscricao_com_limite'
    # 2. Soma o número de inscritos nas oficinas com tipo_inscricao 'com_inscricao_sem_limite'
    total_vagas = 0
    for of in oficinas:
        if of.tipo_inscricao == 'com_inscricao_com_limite':
            total_vagas += of.vagas
        elif of.tipo_inscricao == 'com_inscricao_sem_limite':
            total_vagas += len(of.inscritos)
    
    total_inscricoes = Inscricao.query.join(Oficina).filter(
        (Oficina.cliente_id == current_user.id) | (Oficina.cliente_id.is_(None))
    ).count()
    percentual_adesao = (total_inscricoes / total_vagas) * 100 if total_vagas > 0 else 0

    # Busca apenas check-ins via QR dos usuários do cliente
    from sqlalchemy import or_

    checkins_via_qr = (
        Checkin.query
        .outerjoin(Checkin.oficina)
        .outerjoin(Checkin.usuario)
        .filter(
            Checkin.palavra_chave.in_(['QR-AUTO', 'QR-EVENTO']),
            or_(
                Usuario.cliente_id == current_user.id,
                Oficina.cliente_id == current_user.id,
                Checkin.cliente_id == current_user.id  # segurança extra
            )
        )
        .order_by(Checkin.data_hora.desc())
        .all()
    )


    # Se for para filtrar pela coluna Inscricao.cliente_id:
    inscritos = Inscricao.query.filter(
        (Inscricao.cliente_id == current_user.id) | (Inscricao.cliente_id.is_(None))
    ).all()
    
     # Buscar eventos ativos
    eventos_ativos = Evento.query.filter_by(cliente_id=current_user.id).all()
    total_eventos = len(eventos_ativos)
    
    # Dados para cards
    agendamentos_totais = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id
    ).scalar() or 0
    
    agendamentos_confirmados = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status == 'confirmado'
    ).scalar() or 0
    
    agendamentos_realizados = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status == 'realizado'
    ).scalar() or 0
    
    agendamentos_cancelados = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status == 'cancelado'
    ).scalar() or 0
    
    # Total de visitantes
    total_visitantes = db.session.query(func.sum(AgendamentoVisita.quantidade_alunos)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status.in_(['confirmado', 'realizado'])
    ).scalar() or 0
    
    # Agendamentos para hoje
    hoje = datetime.utcnow().date()
    agendamentos_hoje = AgendamentoVisita.query.join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data == hoje,
        AgendamentoVisita.status == 'confirmado'
    ).order_by(
        HorarioVisitacao.horario_inicio
    ).all()
    
    # Próximos agendamentos (próximos 7 dias, excluindo hoje)
    data_limite = hoje + timedelta(days=7)
    proximos_agendamentos = AgendamentoVisita.query.join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data > hoje,
        HorarioVisitacao.data <= data_limite,
        AgendamentoVisita.status == 'confirmado'
    ).order_by(
        HorarioVisitacao.data,
        HorarioVisitacao.horario_inicio
    ).limit(5).all()
    
    # Calcular ocupação média (vagas preenchidas / capacidade total) 
    ocupacao_query = db.session.query(
        func.sum(HorarioVisitacao.capacidade_total - HorarioVisitacao.vagas_disponiveis).label('ocupadas'),
        func.sum(HorarioVisitacao.capacidade_total).label('total')
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data >= hoje
    ).first()
    
    ocupacao_media = 0
    if ocupacao_query and ocupacao_query.total and ocupacao_query.total > 0:
        ocupacao_media = (ocupacao_query.ocupadas / ocupacao_query.total) * 100

    
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
        config_cliente=config_cliente,
        eventos_ativos=eventos_ativos,
        agendamentos_totais=agendamentos_totais,
        agendamentos_confirmados=agendamentos_confirmados,
        agendamentos_realizados=agendamentos_realizados,
        agendamentos_cancelados=agendamentos_cancelados,
        total_visitantes=total_visitantes,
        agendamentos_hoje=agendamentos_hoje,
        proximos_agendamentos=proximos_agendamentos,
        ocupacao_media=ocupacao_media,
        total_eventos=total_eventos,
        eventos=eventos
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

@dashboard_routes.route('/dashboard_aba_agendamentos')
@login_required
def dashboard_aba_agendamentos():
    """
    Rota para carregar os dados da aba de agendamentos no dashboard do cliente.
    Esta rota é projetada para ser chamada via AJAX para popular a aba de agendamentos.
    """
    # Verificar se é um cliente
    if current_user.tipo != 'cliente':
        return jsonify(error='Acesso negado'), 403
    
    # Buscar eventos ativos
    eventos_ativos = Evento.query.filter_by(
        cliente_id=current_user.id
    ).filter(
        and_(
            Evento.data_inicio <= datetime.utcnow(),
            Evento.data_fim >= datetime.utcnow(),
            Evento.status == 'ativo'
        )
    ).all()
    
    # Dados para cards
    agendamentos_totais = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id
    ).scalar() or 0
    
    agendamentos_confirmados = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status == 'confirmado'
    ).scalar() or 0
    
    agendamentos_realizados = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status == 'realizado'
    ).scalar() or 0
    
    agendamentos_cancelados = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status == 'cancelado'
    ).scalar() or 0
    
    # Total de visitantes
    total_visitantes = db.session.query(func.sum(AgendamentoVisita.quantidade_alunos)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status.in_(['confirmado', 'realizado'])
    ).scalar() or 0
    
    # Agendamentos para hoje
    hoje = datetime.utcnow().date()
    agendamentos_hoje = AgendamentoVisita.query.join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data == hoje,
        AgendamentoVisita.status == 'confirmado'
    ).order_by(
        HorarioVisitacao.horario_inicio
    ).all()
    
    # Próximos agendamentos (próximos 7 dias, excluindo hoje)
    data_limite = hoje + timedelta(days=7)
    proximos_agendamentos = AgendamentoVisita.query.join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data > hoje,
        HorarioVisitacao.data <= data_limite,
        AgendamentoVisita.status == 'confirmado'
    ).order_by(
        HorarioVisitacao.data,
        HorarioVisitacao.horario_inicio
    ).limit(5).all()
    
    # Calcular ocupação média (vagas preenchidas / capacidade total) 
    ocupacao_query = db.session.query(
        func.sum(HorarioVisitacao.capacidade_total - HorarioVisitacao.vagas_disponiveis).label('ocupadas'),
        func.sum(HorarioVisitacao.capacidade_total).label('total')
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data >= hoje
    ).first()
    
    ocupacao_media = 0
    if ocupacao_query and ocupacao_query.total and ocupacao_query.total > 0:
        ocupacao_media = (ocupacao_query.ocupadas / ocupacao_query.total) * 100
    
    # Se for uma requisição AJAX, retornar JSON com os dados
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'eventos_ativos_count': len(eventos_ativos),
            'agendamentos_totais': agendamentos_totais,
            'agendamentos_confirmados': agendamentos_confirmados,
            'agendamentos_realizados': agendamentos_realizados,
            'agendamentos_cancelados': agendamentos_cancelados,
            'total_visitantes': total_visitantes,
            'ocupacao_media': round(ocupacao_media, 1) if ocupacao_media else 0,
            # Não é possível enviar objetos complexos via JSON, então apenas enviamos
            # um sinal de que há ou não agendamentos
            'tem_agendamentos_hoje': len(agendamentos_hoje) > 0,
            'tem_proximos_agendamentos': len(proximos_agendamentos) > 0
        })
    
    # Renderizar o template HTML da aba ou redirecionar para o dashboard
    # Dependendo de como sua aplicação lida com as abas
    return render_template(
        'partials/dashboard_agendamentos_aba.html',
        eventos_ativos=eventos_ativos,
        agendamentos_totais=agendamentos_totais,
        agendamentos_confirmados=agendamentos_confirmados,
        agendamentos_realizados=agendamentos_realizados,
        agendamentos_cancelados=agendamentos_cancelados,
        total_visitantes=total_visitantes,
        agendamentos_hoje=agendamentos_hoje,
        proximos_agendamentos=proximos_agendamentos,
        ocupacao_media=ocupacao_media
    )

@dashboard_routes.route('/dashboard_aba_agendamentos_hoje')
@login_required
def dashboard_aba_agendamentos_hoje():
    """
    Rota para obter apenas os agendamentos de hoje para atualização dinâmica.
    """
    if current_user.tipo != 'cliente':
        return jsonify(error='Acesso negado'), 403
    
    hoje = datetime.utcnow().date()
    agendamentos_hoje = AgendamentoVisita.query.join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data == hoje,
        AgendamentoVisita.status == 'confirmado'
    ).order_by(
        HorarioVisitacao.horario_inicio
    ).all()
    
    return render_template(
        'partials/agendamentos_hoje_lista.html',
        agendamentos_hoje=agendamentos_hoje
    )

@dashboard_routes.route('/dashboard_aba_proximos_agendamentos')
@login_required
def dashboard_aba_proximos_agendamentos():
    """
    Rota para obter apenas os próximos agendamentos para atualização dinâmica.
    """
    if current_user.tipo != 'cliente':
        return jsonify(error='Acesso negado'), 403
    
    hoje = datetime.utcnow().date()
    data_limite = hoje + timedelta(days=7)
    proximos_agendamentos = AgendamentoVisita.query.join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data > hoje,
        HorarioVisitacao.data <= data_limite,
        AgendamentoVisita.status == 'confirmado'
    ).order_by(
        HorarioVisitacao.data,
        HorarioVisitacao.horario_inicio
    ).limit(5).all()
    
    return render_template(
        'partials/proximos_agendamentos_lista.html',
        proximos_agendamentos=proximos_agendamentos
    )

# Função auxiliar para definir os valores na sessão
def set_dashboard_agendamentos_data():
    """
    Função auxiliar para calcular e armazenar em sessão os dados para a aba de agendamentos.
    Chamada antes de renderizar o dashboard principal para garantir que os dados estejam disponíveis.
    """
    if current_user.tipo != 'cliente':
        return
    
    # Buscar eventos ativos
    eventos_ativos = Evento.query.filter_by(
        cliente_id=current_user.id
    ).filter(
        and_(
            Evento.data_inicio <= datetime.utcnow(),
            Evento.data_fim >= datetime.utcnow(),
            Evento.status == 'ativo'
        )
    ).all()
    
    # Dados para cards
    agendamentos_totais = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id
    ).scalar() or 0
    
    agendamentos_confirmados = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status == 'confirmado'
    ).scalar() or 0
    
    agendamentos_realizados = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status == 'realizado'
    ).scalar() or 0
    
    agendamentos_cancelados = db.session.query(func.count(AgendamentoVisita.id)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status == 'cancelado'
    ).scalar() or 0
    
    # Total de visitantes
    total_visitantes = db.session.query(func.sum(AgendamentoVisita.quantidade_alunos)).join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        AgendamentoVisita.status.in_(['confirmado', 'realizado'])
    ).scalar() or 0
    
    # Agendamentos para hoje
    hoje = datetime.utcnow().date()
    agendamentos_hoje = AgendamentoVisita.query.join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data == hoje,
        AgendamentoVisita.status == 'confirmado'
    ).order_by(
        HorarioVisitacao.horario_inicio
    ).all()
    
    # Próximos agendamentos (próximos 7 dias, excluindo hoje)
    data_limite = hoje + timedelta(days=7)
    proximos_agendamentos = AgendamentoVisita.query.join(
        HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data > hoje,
        HorarioVisitacao.data <= data_limite,
        AgendamentoVisita.status == 'confirmado'
    ).order_by(
        HorarioVisitacao.data,
        HorarioVisitacao.horario_inicio
    ).limit(5).all()
    
    # Calcular ocupação média (vagas preenchidas / capacidade total) 
    ocupacao_query = db.session.query(
        func.sum(HorarioVisitacao.capacidade_total - HorarioVisitacao.vagas_disponiveis).label('ocupadas'),
        func.sum(HorarioVisitacao.capacidade_total).label('total')
    ).join(
        Evento, HorarioVisitacao.evento_id == Evento.id
    ).filter(
        Evento.cliente_id == current_user.id,
        HorarioVisitacao.data >= hoje
    ).first()
    
    ocupacao_media = 0
    if ocupacao_query and ocupacao_query.total and ocupacao_query.total > 0:
        ocupacao_media = (ocupacao_query.ocupadas / ocupacao_query.total) * 100
    
    # Armazenar valores na sessão para uso no template principal
    session['dashboard_agendamentos'] = {
        'eventos_ativos': len(eventos_ativos),
        'agendamentos_totais': agendamentos_totais,
        'agendamentos_confirmados': agendamentos_confirmados,
        'agendamentos_realizados': agendamentos_realizados,
        'agendamentos_cancelados': agendamentos_cancelados,
        'total_visitantes': total_visitantes,
        'ocupacao_media': round(ocupacao_media, 1) if ocupacao_media else 0,
        'tem_agendamentos_hoje': len(agendamentos_hoje) > 0,
        'tem_proximos_agendamentos': len(proximos_agendamentos) > 0,
        'timestamp': datetime.utcnow().timestamp()
    }
    
    # Passar os objetos para o contexto global
    return {
        'eventos_ativos': eventos_ativos,
        'agendamentos_totais': agendamentos_totais,
        'agendamentos_confirmados': agendamentos_confirmados,
        'agendamentos_realizados': agendamentos_realizados,
        'agendamentos_cancelados': agendamentos_cancelados,
        'total_visitantes': total_visitantes,
        'agendamentos_hoje': agendamentos_hoje,
        'proximos_agendamentos': proximos_agendamentos,
        'ocupacao_media': ocupacao_media
    }

@dashboard_routes.route('/dashboard-agendamentos')
@login_required
def dashboard_agendamentos():
    # Inicializar variáveis vazias/padrão para o template
    eventos_ativos = []
    agendamentos_totais = 0
    total_visitantes = 0
    ocupacao_media = 0
    agendamentos_confirmados = 0
    agendamentos_realizados = 0
    agendamentos_cancelados = 0
    agendamentos_hoje = []
    proximos_agendamentos = []
    todos_agendamentos = []
    periodos_agendamento = []
    config_agendamento = None
    
    # Buscar eventos do cliente atual
    try:
        eventos_ativos = Evento.query.filter_by(cliente_id=current_user.id).all()
    except Exception as e:
        flash(f"Erro ao buscar eventos: {str(e)}", "danger")
    
    # Verificar se temos dados suficientes para mostrar a página básica
    return render_template('dashboard_agendamentos.html', 
                          eventos_ativos=eventos_ativos,
                          agendamentos_totais=agendamentos_totais,
                          total_visitantes=total_visitantes,
                          ocupacao_media=ocupacao_media,
                          agendamentos_confirmados=agendamentos_confirmados,
                          agendamentos_realizados=agendamentos_realizados,
                          agendamentos_cancelados=agendamentos_cancelados,
                          agendamentos_hoje=agendamentos_hoje,
                          proximos_agendamentos=proximos_agendamentos,
                          todos_agendamentos=todos_agendamentos,
                          periodos_agendamento=periodos_agendamento,
                          config_agendamento=config_agendamento)
