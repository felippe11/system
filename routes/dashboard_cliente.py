from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
)
from flask_login import login_required, current_user
from extensions import db
import logging
from utils import endpoints

logger = logging.getLogger(__name__)
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from models import (
Evento, Oficina, Inscricao, Checkin,
ConfiguracaoCliente, AgendamentoVisita, HorarioVisitacao, Usuario,
EventoInscricaoTipo, Configuracao, ReviewerApplication,
RevisorCandidatura, RevisorProcess
)

# Modelos opcionais usados no dashboard de agendamentos. Em alguns ambientes
# eles podem não estar disponíveis (por exemplo, em testes ou em instalações
# parciais). O uso de try/except garante que o módulo funcione mesmo na
# ausência desses modelos.
try:  # pragma: no cover - importação opcional
    from models import ConfigAgendamento  # type: ignore
except Exception:  # pragma: no cover - silenciosamente ignora ausência
    ConfigAgendamento = None  # type: ignore

try:  # pragma: no cover - importação opcional
    from models import PeriodoAgendamento  # type: ignore
except Exception:  # pragma: no cover
    PeriodoAgendamento = None  # type: ignore

# Importa o blueprint central para registrar as rotas deste módulo
from .dashboard_routes import dashboard_routes

@dashboard_routes.route('/dashboard_cliente')
@login_required
def dashboard_cliente():
    """Renderiza o painel do cliente com estatísticas e candidaturas."""
    if current_user.tipo != 'cliente':
        return redirect(url_for(endpoints.DASHBOARD))

    logger.debug("Cliente autenticado: %s (ID: %s)", current_user.email, current_user.id)
    logger.debug("Usuário logado: %s", current_user.email)
    logger.debug("ID: %s", current_user.id)
    logger.debug("Tipo: %s", current_user.tipo if hasattr(current_user, 'tipo') else "N/A")


    data = {
        'oficinas': [],
        'total_oficinas': 0,
        'total_vagas': 0,
        'total_inscricoes': 0,
        'percentual_adesao': 0,
        'checkins_via_qr': [],
        'inscritos': [],
        'config_cliente': None,
        'eventos_ativos': [],
        'agendamentos_totais': 0,
        'agendamentos_confirmados': 0,
        'agendamentos_realizados': 0,
        'agendamentos_cancelados': 0,
        'total_visitantes': 0,
        'agendamentos_hoje': [],
        'proximos_agendamentos': [],
        'ocupacao_media': 0,
        'total_eventos': 0,
        'eventos': [],
        'finance_data': [],
        'valor_caixa': 0,
        'reviewer_apps': [],
        'revisor_candidaturas': [],
        'revisor_candidaturas_aprovadas': [],
    }
    try:
        eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
        logger.debug("Eventos: %s", eventos)
        data['eventos'] = eventos

        oficinas = Oficina.query.filter_by(cliente_id=current_user.id).all()
        data['oficinas'] = oficinas
        data['total_oficinas'] = len(oficinas)

        total_vagas = 0
        for of in oficinas:
            if of.tipo_inscricao == 'com_inscricao_com_limite':
                total_vagas += of.vagas
            elif of.tipo_inscricao == 'com_inscricao_sem_limite':
                total_vagas += len(of.inscritos)
        data['total_vagas'] = total_vagas

        total_inscricoes = Inscricao.query.join(Oficina).filter(
            (Oficina.cliente_id == current_user.id) | (Oficina.cliente_id.is_(None))
        ).count()
        data['total_inscricoes'] = total_inscricoes
        data['percentual_adesao'] = (
            (total_inscricoes / total_vagas) * 100 if total_vagas > 0 else 0
        )

        checkins_via_qr = (
            Checkin.query
            .outerjoin(Checkin.oficina)
            .outerjoin(Checkin.usuario)
            .filter(
                Checkin.palavra_chave.in_(['QR-AUTO', 'QR-EVENTO', 'QR-OFICINA']),
                or_(
                    Usuario.cliente_id == current_user.id,
                    Oficina.cliente_id == current_user.id,
                    Checkin.cliente_id == current_user.id,
                ),
            )
            .order_by(Checkin.data_hora.desc())
            .all()
        )
        data['checkins_via_qr'] = checkins_via_qr

        inscritos = Inscricao.query.filter(
            (Inscricao.cliente_id == current_user.id)
            | (Inscricao.cliente_id.is_(None))
        ).all()
        data['inscritos'] = inscritos

        eventos_ativos = Evento.query.filter_by(cliente_id=current_user.id).all()
        data['eventos_ativos'] = eventos_ativos
        data['total_eventos'] = len(eventos_ativos)

        agendamentos_totais = db.session.query(
            func.count(AgendamentoVisita.id)
        ).join(
            HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
        ).join(
            Evento, HorarioVisitacao.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == current_user.id
        ).scalar() or 0
        data['agendamentos_totais'] = agendamentos_totais

        agendamentos_confirmados = db.session.query(
            func.count(AgendamentoVisita.id)
        ).join(
            HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
        ).join(
            Evento, HorarioVisitacao.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == current_user.id,
            AgendamentoVisita.status == 'confirmado',
        ).scalar() or 0
        data['agendamentos_confirmados'] = agendamentos_confirmados

        agendamentos_realizados = db.session.query(
            func.count(AgendamentoVisita.id)
        ).join(
            HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
        ).join(
            Evento, HorarioVisitacao.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == current_user.id,
            AgendamentoVisita.status == 'realizado',
        ).scalar() or 0
        data['agendamentos_realizados'] = agendamentos_realizados

        agendamentos_cancelados = db.session.query(
            func.count(AgendamentoVisita.id)
        ).join(
            HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
        ).join(
            Evento, HorarioVisitacao.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == current_user.id,
            AgendamentoVisita.status == 'cancelado',
        ).scalar() or 0
        data['agendamentos_cancelados'] = agendamentos_cancelados

        total_visitantes = db.session.query(
            func.sum(AgendamentoVisita.quantidade_alunos)
        ).join(
            HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
        ).join(
            Evento, HorarioVisitacao.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == current_user.id,
            AgendamentoVisita.status.in_(['confirmado', 'realizado']),
        ).scalar() or 0
        data['total_visitantes'] = total_visitantes

        hoje = datetime.utcnow().date()
        agendamentos_hoje = AgendamentoVisita.query.join(
            HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
        ).join(
            Evento, HorarioVisitacao.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == current_user.id,
            HorarioVisitacao.data == hoje,
            AgendamentoVisita.status.in_(['pendente', 'confirmado']),
        ).order_by(
            HorarioVisitacao.horario_inicio
        ).all()
        data['agendamentos_hoje'] = agendamentos_hoje

        data_limite = hoje + timedelta(days=7)
        proximos_agendamentos = AgendamentoVisita.query.join(
            HorarioVisitacao, AgendamentoVisita.horario_id == HorarioVisitacao.id
        ).join(
            Evento, HorarioVisitacao.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == current_user.id,
            HorarioVisitacao.data > hoje,
            HorarioVisitacao.data <= data_limite,
            AgendamentoVisita.status.in_(['pendente', 'confirmado']),
        ).order_by(
            HorarioVisitacao.data,
            HorarioVisitacao.horario_inicio,
        ).limit(5).all()
        data['proximos_agendamentos'] = proximos_agendamentos

        ocupacao_query = db.session.query(
            func.sum(
                HorarioVisitacao.capacidade_total - HorarioVisitacao.vagas_disponiveis
            ).label('ocupadas'),
            func.sum(HorarioVisitacao.capacidade_total).label('total'),
        ).join(
            Evento, HorarioVisitacao.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == current_user.id,
            HorarioVisitacao.data >= hoje,
        ).first()
        if (
            ocupacao_query and ocupacao_query.total and ocupacao_query.total > 0
        ):
            data['ocupacao_media'] = (
                ocupacao_query.ocupadas / ocupacao_query.total
            ) * 100

        config_cliente = ConfiguracaoCliente.query.filter_by(
            cliente_id=current_user.id
        ).first()
        if not config_cliente:
            config_cliente = ConfiguracaoCliente(
                cliente_id=current_user.id,
                permitir_checkin_global=False,
                habilitar_feedback=False,
                habilitar_certificado_individual=False,
            )
            db.session.add(config_cliente)
            db.session.commit()
        data['config_cliente'] = config_cliente

        finance_data = db.session.query(
            EventoInscricaoTipo.nome.label('nome'),
            func.count(Inscricao.id).label('quantidade'),
            EventoInscricaoTipo.preco.label('preco'),
        ).join(
            Evento, Evento.id == EventoInscricaoTipo.evento_id
        ).join(
            Inscricao, Inscricao.tipo_inscricao_id == EventoInscricaoTipo.id
        ).filter(
            Evento.cliente_id == current_user.id,
            Inscricao.status_pagamento == 'approved',
        ).group_by(
            EventoInscricaoTipo.id
        ).order_by(
            func.count(Inscricao.id).desc()
        ).all()
        data['finance_data'] = finance_data
        data['valor_caixa'] = sum(
            float(r.preco) * r.quantidade for r in finance_data
        )

        data['reviewer_apps'] = ReviewerApplication.query.all()

        revisor_candidaturas = (
            RevisorCandidatura.query
            .join(RevisorProcess, RevisorCandidatura.process_id == RevisorProcess.id)
            .filter(RevisorProcess.cliente_id == current_user.id)
            .all()
        )
        data['revisor_candidaturas'] = revisor_candidaturas

        revisor_candidaturas_aprovadas = (
            RevisorCandidatura.query
            .join(RevisorProcess, RevisorCandidatura.process_id == RevisorProcess.id)
            .filter(
                RevisorProcess.cliente_id == current_user.id,
                RevisorCandidatura.status == 'aprovado',
            )
            .all()
        )
        data['revisor_candidaturas_aprovadas'] = revisor_candidaturas_aprovadas
    except SQLAlchemyError as exc:
        logger.exception('Erro ao carregar dashboard do cliente: %s', exc)
        flash('Não foi possível carregar o dashboard do cliente.', 'error')

    return render_template(
        'dashboard_cliente.html',
        usuario=current_user,
        **data,
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
        AgendamentoVisita.status.in_(['pendente', 'confirmado'])
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
        AgendamentoVisita.status.in_(['pendente', 'confirmado'])
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
        AgendamentoVisita.status.in_(['pendente', 'confirmado'])
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
        AgendamentoVisita.status.in_(['pendente', 'confirmado'])
    ).order_by(
        HorarioVisitacao.data,
        HorarioVisitacao.horario_inicio
    ).limit(5).all()
    
    return render_template(
        'partials/proximos_agendamentos_lista.html',
        proximos_agendamentos=proximos_agendamentos
    )

@dashboard_routes.route('/dashboard_aba_financeiro')
@login_required
def dashboard_aba_financeiro():
    """Rota para exibir resumo financeiro."""
    if current_user.tipo != 'cliente':
        return jsonify(error='Acesso negado'), 403

    finance_data = (
        db.session.query(
            EventoInscricaoTipo.nome.label('nome'),
            func.count(Inscricao.id).label('quantidade'),
            EventoInscricaoTipo.preco.label('preco')
        )
        .join(Evento, Evento.id == EventoInscricaoTipo.evento_id)
        .join(Inscricao, Inscricao.tipo_inscricao_id == EventoInscricaoTipo.id)
        .filter(
            Evento.cliente_id == current_user.id,
            Inscricao.status_pagamento == 'approved'
        )
        .group_by(EventoInscricaoTipo.id)
        .order_by(func.count(Inscricao.id).desc())
        .all()
    )

    valor_caixa = sum(float(r.preco) * r.quantidade for r in finance_data)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'tipos': [
                {
                    'nome': r.nome,
                    'quantidade': r.quantidade,
                    'preco': float(r.preco)
                } for r in finance_data
            ],
            'valor_caixa': valor_caixa
        })

    return render_template(
        'partials/dashboard_financeiro_aba.html',
        tipos=finance_data,
        valor_caixa=valor_caixa
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
        AgendamentoVisita.status.in_(['pendente', 'confirmado'])
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
        AgendamentoVisita.status.in_(['pendente', 'confirmado'])
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

    # Períodos de agendamento e configuração opcional
    periodos_agendamento = []
    if PeriodoAgendamento:  # pragma: no branch - depende da existência do modelo
        periodos_agendamento = PeriodoAgendamento.query.join(
            Evento, PeriodoAgendamento.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == current_user.id
        ).all()

    config_agendamento = None
    if ConfigAgendamento:  # pragma: no branch
        config_agendamento = ConfigAgendamento.query.filter_by(
            cliente_id=current_user.id
        ).first()

    # Armazenar valores na sessão para uso no template principal
    session['dashboard_agendamentos'] = {
        'eventos_ativos': len(eventos_ativos),
        'agendamentos_totais': agendamentos_totais,
        'agendamentos_confirmados': agendamentos_confirmados,
        'agendamentos_realizados': agendamentos_realizados,
        'agendamentos_cancelados': agendamentos_cancelados,
        'total_visitantes': total_visitantes,
        'ocupacao_media': round(ocupacao_media, 1) if ocupacao_media else 0,
        'agendamentos_hoje': len(agendamentos_hoje),
        'proximos_agendamentos': len(proximos_agendamentos),
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
        'ocupacao_media': ocupacao_media,
        'periodos_agendamento': periodos_agendamento,
        'config_agendamento': config_agendamento
    }

@dashboard_routes.route('/dashboard-agendamentos')
@login_required
def dashboard_agendamentos():
    """Dashboard específico do módulo de agendamentos."""
    # Valores padrão para evitar erros de renderização
    context = {
        'eventos_ativos': [],
        'agendamentos_totais': 0,
        'total_visitantes': 0,
        'ocupacao_media': 0,
        'agendamentos_confirmados': 0,
        'agendamentos_realizados': 0,
        'agendamentos_cancelados': 0,
        'agendamentos_hoje': [],
        'proximos_agendamentos': [],
        'periodos_agendamento': [],
        'config_agendamento': None,
    }

    try:
        data = set_dashboard_agendamentos_data()
        if data:
            context.update(data)
    except Exception as e:  # pragma: no cover - apenas loga erros inesperados
        flash(f"Erro ao carregar dados do dashboard de agendamentos: {str(e)}", "danger")

    return render_template('agendamento/dashboard_agendamentos.html', **context)

@dashboard_routes.route('/reviewer_applications/<int:app_id>', methods=['POST'])
@login_required
def update_reviewer_application(app_id):
    """Atualiza o estágio ou status de uma candidatura de revisor."""
    if current_user.tipo not in ('cliente', 'admin'):
        return redirect(url_for(endpoints.DASHBOARD))

    action = request.form.get('action')
    if request.is_json and not action:
        action = request.json.get('action')
    app_obj = ReviewerApplication.query.get_or_404(app_id)

    if action == 'advance':
        stages = ['novo', 'triagem', 'avaliacao', 'aprovado']
        try:
            idx = stages.index(app_obj.stage)
            if idx < len(stages) - 1:
                app_obj.stage = stages[idx + 1]
        except ValueError:
            app_obj.stage = 'triagem'
    elif action == 'approve':
        app_obj.stage = 'aprovado'
        if app_obj.usuario:
            app_obj.usuario.tipo = 'revisor'
    elif action == 'reject':
        app_obj.stage = 'rejeitado'
    db.session.commit()

    if request.is_json:
        return {'success': True}
    return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
