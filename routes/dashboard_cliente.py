from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
    send_file,
    abort,
)
from flask_login import login_required, current_user
from extensions import db
import logging
from utils import endpoints
from utils.barema import normalize_barema_requisitos
from collections import defaultdict

logger = logging.getLogger(__name__)
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import json
from io import BytesIO
from models import (
    Evento,
    Oficina,
    Inscricao,
    Checkin,
    ConfiguracaoCliente,
    AgendamentoVisita,
    HorarioVisitacao,
    Usuario,
    EventoInscricaoTipo,
    Configuracao,
    ReviewerApplication,
    RevisorCandidatura,
    RevisorProcess,
    Formulario,
    WorkMetadata,
)
from models.avaliacao import AvaliacaoBarema, AvaliacaoCriterio
from models.event import RespostaFormulario
from models.review import Submission, Assignment
from routes.revisor_routes import resolve_categoria_trabalho

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

        data['revisor_filter_options'] = _build_revisor_filter_options(
            revisor_candidaturas
        )

        formulario_trabalho = Formulario.query.filter_by(
            nome='Formulário de Trabalhos'
        ).first()
        data['formulario_trabalho'] = formulario_trabalho
    except SQLAlchemyError as exc:
        logger.exception('Erro ao carregar dashboard do cliente: %s', exc)
        flash('Não foi possível carregar o dashboard do cliente.', 'error')

    return render_template(
        'dashboard_cliente.html',
        usuario=current_user,
        **data,
    )


def _build_revisor_filter_options(candidaturas):
    """Create filter metadata based on reviewer application responses."""
    question_values: dict[str, dict[str, str]] = defaultdict(dict)

    for candidatura in candidaturas:
        respostas = getattr(candidatura, 'respostas', None) or {}
        if not isinstance(respostas, dict):
            continue

        for pergunta, valor in respostas.items():
            if not pergunta:
                continue

            raw_values = valor if isinstance(valor, list) else [valor]
            for raw_value in raw_values:
                sanitized_value = _sanitize_filter_value(raw_value)
                value_key = sanitized_value or '__EMPTY__'
                if value_key not in question_values[pergunta]:
                    question_values[pergunta][value_key] = (
                        sanitized_value if sanitized_value else 'Não informado'
                    )

    filter_options = []
    for pergunta in sorted(question_values.keys()):
        options_map = question_values[pergunta]

        sorted_options = sorted(
            options_map.items(),
            key=lambda item: (
                1 if item[0] == '__EMPTY__' else 0,
                item[1].lower(),
            ),
        )

        filter_options.append(
            {
                'question': pergunta,
                'options': [
                    {'value': value_key, 'label': label}
                    for value_key, label in sorted_options
                ],
            }
        )

    return filter_options


def _sanitize_filter_value(value):
    """Normalize filter values for consistent comparisons."""
    if value is None:
        return ''
    if isinstance(value, (list, dict)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return str(value).strip()
    
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

@dashboard_routes.route('/gerenciar_baremas/<int:evento_id>')
@login_required
def gerenciar_baremas(evento_id):
    """Página para gerenciar baremas por categoria de um evento."""
    if current_user.tipo not in ('cliente', 'admin'):
        return redirect(url_for(endpoints.DASHBOARD))

    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first_or_404()

    # Buscar categorias disponíveis do formulário de trabalhos
    categorias_formulario = []
    try:
        from models.formulario import CampoFormulario
        campo_categoria = CampoFormulario.query.filter_by(
            nome='Categoria',
            formulario_id=9  # Formulário de Trabalhos
        ).first()
        if campo_categoria and campo_categoria.opcoes:
            categorias_formulario = [
                opt.strip() for opt in campo_categoria.opcoes.split(',') if opt.strip()
            ]
    except ImportError:
        categorias_formulario = [
            'Prática Educacional',
            'Pesquisa Inovadora',
            'Produto Inovador',
        ]

    # Consolidar categorias vindas do formulário, metadados e submissões importadas
    categorias_map = {}

    for categoria in categorias_formulario:
        categoria_limpa = categoria.strip()
        if not categoria_limpa:
            continue
        chave = categoria_limpa.lower()
        categorias_map.setdefault(chave, categoria_limpa)

    # Categorias vindas dos metadados de trabalhos importados
    metadata_categorias = (
        db.session.query(WorkMetadata.categoria)
        .filter(WorkMetadata.evento_id == evento_id)
        .filter(WorkMetadata.categoria.isnot(None))
        .distinct()
        .all()
    )
    for (categoria_metadata,) in metadata_categorias:
        if categoria_metadata is None:
            continue
        categoria_limpa = str(categoria_metadata).strip()
        if categoria_limpa:
            chave = categoria_limpa.lower()
            categorias_map.setdefault(chave, categoria_limpa)

    # Categorias declaradas diretamente nas submissões (planilhas Excel)
    submission_attrs = (
        db.session.query(Submission.attributes)
        .filter(Submission.evento_id == evento_id)
        .all()
    )
    for (attributes,) in submission_attrs:
        if not isinstance(attributes, dict):
            continue
        categoria_attr = attributes.get('categoria') or attributes.get('Categoria')
        if not categoria_attr:
            continue
        categoria_limpa = str(categoria_attr).strip()
        if categoria_limpa:
            chave = categoria_limpa.lower()
            categorias_map.setdefault(chave, categoria_limpa)

    categorias = list(categorias_map.values())

    # Buscar baremas existentes para este evento
    from models.review import CategoriaBarema
    baremas_existentes = CategoriaBarema.query.filter_by(evento_id=evento_id).all()

    return render_template('dashboard/gerenciar_baremas.html', 
                         evento=evento, 
                         categorias=categorias,
                         baremas_existentes=baremas_existentes)

@dashboard_routes.route('/criar_barema/<int:evento_id>/<categoria>', methods=['GET', 'POST'])
@login_required
def criar_editar_barema(evento_id, categoria):
    """Criar ou editar barema para uma categoria específica."""
    if current_user.tipo not in ('cliente', 'admin'):
        return redirect(url_for(endpoints.DASHBOARD))
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first_or_404()
    
    from models.review import CategoriaBarema
    barema = CategoriaBarema.query.filter_by(
        evento_id=evento_id, 
        categoria=categoria
    ).first()
    
    if request.method == 'POST':
        nome = request.form.get('nome', f'Barema - {categoria}')
        descricao = request.form.get('descricao', '')
        
        # Processar critérios do formulário
        criterios = {}
        i = 0

        while f'criterio_{i}_nome' in request.form:
            criterio_nome = request.form.get(f'criterio_{i}_nome')
            criterio_max = request.form.get(f'criterio_{i}_max', type=float)
            criterio_min = request.form.get(f'criterio_{i}_min', type=float)
            criterio_descricao = request.form.get(f'criterio_{i}_descricao', '')

            if criterio_nome and criterio_max:
                min_value = criterio_min if isinstance(criterio_min, (int, float)) else 0
                if min_value is None or min_value < 0:
                    min_value = 0
                criterios[criterio_nome] = {
                    'nome': criterio_nome,
                    'pontuacao_max': criterio_max,
                    'pontuacao_min': min_value,
                    'nota_minima_justificativa': min_value,
                    'descricao': criterio_descricao
                }
            i += 1
        
        if not barema:
            barema = CategoriaBarema(
                evento_id=evento_id,
                categoria=categoria,
                nome=nome,
                descricao=descricao,
                criterios=criterios
            )
            db.session.add(barema)
        else:
            barema.nome = nome
            barema.descricao = descricao
            barema.criterios = criterios
        
        db.session.commit()
        flash(f'Barema para categoria "{categoria}" salvo com sucesso!', 'success')
        return redirect(url_for('dashboard_routes.gerenciar_baremas', evento_id=evento_id))
    
    return render_template('dashboard/criar_editar_barema.html', 
                         evento=evento, 
                         categoria=categoria,
                         barema=barema)

@dashboard_routes.route('/deletar_barema/<int:barema_id>', methods=['POST'])
@login_required
def deletar_barema(barema_id):
    """Deletar um barema específico."""
    if current_user.tipo not in ('cliente', 'admin'):
        return redirect(url_for(endpoints.DASHBOARD))
    
    from models.review import CategoriaBarema
    barema = CategoriaBarema.query.get_or_404(barema_id)
    
    # Verificar se o barema pertence a um evento do cliente
    evento = Evento.query.filter_by(id=barema.evento_id, cliente_id=current_user.id).first_or_404()
    
    categoria = barema.categoria
    db.session.delete(barema)
    db.session.commit()
    
    flash(f'Barema da categoria "{categoria}" deletado com sucesso!', 'success')
    return redirect(url_for('dashboard_routes.gerenciar_baremas', evento_id=evento.id))

@dashboard_routes.route('/testar_barema/<int:evento_id>/<categoria>', methods=['GET', 'POST'])
@login_required
def testar_barema(evento_id, categoria):
    """Testar um barema como formulário de avaliação."""
    if current_user.tipo not in ('cliente', 'admin'):
        return redirect(url_for(endpoints.DASHBOARD))
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first_or_404()
    
    from models.review import CategoriaBarema
    barema = CategoriaBarema.query.filter_by(
        evento_id=evento_id, 
        categoria=categoria
    ).first()
    
    if not barema:
        flash(f'Barema não encontrado para a categoria "{categoria}".', 'warning')
        return redirect(url_for('dashboard_routes.gerenciar_baremas', evento_id=evento_id))
    
    requisitos = normalize_barema_requisitos(barema)
    if not requisitos:
        flash('Barema sem critérios configurados para teste.', 'warning')
        return redirect(url_for('dashboard_routes.gerenciar_baremas', evento_id=evento_id))

    if request.method == 'POST':
        # Processar pontuações do formulário de teste
        pontuacoes = {}
        total_pontos = 0

        for criterio_nome, criterio_data in requisitos.items():
            pontuacao = request.form.get(f'criterio_{criterio_nome}', type=float)
            if pontuacao is not None:
                # Validar se a pontuação está dentro do limite
                max_pontos = criterio_data.get('max', 0) or 0
                if 0 <= pontuacao <= max_pontos:
                    pontuacoes[criterio_nome] = pontuacao
                    total_pontos += pontuacao
                else:
                    flash(
                        f'Pontuação para "{criterio_nome}" deve estar entre 0 e {max_pontos}.',
                        'warning'
                    )
                    return redirect(url_for('dashboard_routes.testar_barema', evento_id=evento_id, categoria=categoria))
        
        # Salvar resultado do teste (opcional - pode ser usado para análise)
        from models.review import TesteBarema
        teste = TesteBarema(
            barema_id=barema.id,
            usuario_id=current_user.id,
            pontuacoes=pontuacoes,
            total_pontos=total_pontos
        )
        db.session.add(teste)
        db.session.commit()
        
        flash(f'Teste do barema concluído! Total de pontos: {total_pontos}', 'success')
        return redirect(url_for('dashboard_routes.gerenciar_baremas', evento_id=evento_id))
    
    total_max = sum((dados.get('max') or 0) for dados in requisitos.values())

    return render_template(
        'dashboard/testar_barema.html',
        evento=evento,
        categoria=categoria,
        barema=barema,
        requisitos=requisitos,
        total_max=total_max
    )

def _coletar_metricas_baremas_dados(usuario, categoria_filtro='', periodo_inicio='', periodo_fim='', criterio_filtro='', cliente_id_override=None):
    from models.review import CategoriaBarema

    cliente_id_base = cliente_id_override
    if usuario.tipo == 'cliente':
        cliente_id_base = usuario.id

    avaliacoes_query = (
        db.session.query(AvaliacaoBarema)
        .options(
            joinedload(AvaliacaoBarema.criterios_avaliacao),
            joinedload(AvaliacaoBarema.trabalho),
            joinedload(AvaliacaoBarema.revisor),
        )
        .join(Submission, AvaliacaoBarema.trabalho_id == Submission.id)
    )

    if cliente_id_base:
        avaliacoes_query = (
            avaliacoes_query
            .join(Evento, Submission.evento_id == Evento.id)
            .filter(Evento.cliente_id == cliente_id_base)
        )
    elif usuario.tipo == 'cliente':
        avaliacoes_query = (
            avaliacoes_query
            .join(Evento, Submission.evento_id == Evento.id)
            .filter(Evento.cliente_id == usuario.id)
        )

    if categoria_filtro:
        avaliacoes_query = avaliacoes_query.filter(AvaliacaoBarema.categoria == categoria_filtro)

    if periodo_inicio:
        try:
            data_inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d')
            avaliacoes_query = avaliacoes_query.filter(AvaliacaoBarema.data_avaliacao >= data_inicio)
        except ValueError:
            pass

    if periodo_fim:
        try:
            data_fim = datetime.strptime(periodo_fim, '%Y-%m-%d')
            avaliacoes_query = avaliacoes_query.filter(AvaliacaoBarema.data_avaliacao <= data_fim)
        except ValueError:
            pass

    avaliacoes = avaliacoes_query.all()

    submission_ids = {avaliacao.trabalho_id for avaliacao in avaliacoes if avaliacao.trabalho_id}
    assignment_lookup: dict[tuple[int, int], Assignment] = {}
    if submission_ids:
        assignment_query = (
            db.session.query(Assignment, RespostaFormulario.trabalho_id)
            .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .filter(RespostaFormulario.trabalho_id.in_(submission_ids))
        )
        if cliente_id_base:
            assignment_query = assignment_query.join(Evento, RespostaFormulario.evento_id == Evento.id).filter(Evento.cliente_id == cliente_id_base)
        elif usuario.tipo == 'cliente':
            assignment_query = assignment_query.join(Evento, RespostaFormulario.evento_id == Evento.id).filter(Evento.cliente_id == usuario.id)

        for assignment, trabalho_id in assignment_query.all():
            assignment_lookup[(trabalho_id, assignment.reviewer_id)] = assignment

    categorias_existentes = db.session.query(AvaliacaoBarema.categoria).distinct().all()
    categorias = [cat[0] for cat in categorias_existentes if cat[0]]

    categorias_padrao = ['Prática Educacional', 'Pesquisa Inovadora', 'Produto Inovador']
    for cat in categorias_padrao:
        if cat not in categorias:
            categorias.append(cat)

    criterios_query = db.session.query(AvaliacaoCriterio).join(
        AvaliacaoBarema, AvaliacaoCriterio.avaliacao_id == AvaliacaoBarema.id
    ).join(Submission, AvaliacaoBarema.trabalho_id == Submission.id)

    if cliente_id_base:
        criterios_query = criterios_query.join(Evento, Submission.evento_id == Evento.id).filter(Evento.cliente_id == cliente_id_base)
    elif usuario.tipo == 'cliente':
        criterios_query = criterios_query.join(Evento, Submission.evento_id == Evento.id).filter(Evento.cliente_id == usuario.id)

    if categoria_filtro:
        criterios_query = criterios_query.filter(AvaliacaoBarema.categoria == categoria_filtro)

    if periodo_inicio:
        try:
            data_inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d')
            criterios_query = criterios_query.filter(AvaliacaoBarema.data_avaliacao >= data_inicio)
        except ValueError:
            pass

    if periodo_fim:
        try:
            data_fim = datetime.strptime(periodo_fim, '%Y-%m-%d')
            criterios_query = criterios_query.filter(AvaliacaoBarema.data_avaliacao <= data_fim)
        except ValueError:
            pass

    criterios_avaliacoes = criterios_query.options(joinedload(AvaliacaoCriterio.avaliacao)).all()

    baremas_por_categoria = {}
    for categoria in categorias:
        eventos_cliente = []
        if cliente_id_base:
            eventos_cliente = [e[0] for e in db.session.query(Evento.id).filter(Evento.cliente_id == cliente_id_base).all()]
        elif usuario.tipo == 'cliente':
            eventos_cliente = [e[0] for e in db.session.query(Evento.id).filter(Evento.cliente_id == usuario.id).all()]

        barema_categoria = None
        if eventos_cliente:
            barema_categoria = (
                db.session.query(CategoriaBarema)
                .filter(
                    CategoriaBarema.categoria == categoria,
                    CategoriaBarema.evento_id.in_(eventos_cliente),
                    CategoriaBarema.ativo == True,
                )
                .first()
            )
        if not barema_categoria:
            barema_categoria = (
                db.session.query(CategoriaBarema)
                .filter(
                    CategoriaBarema.categoria == categoria,
                    CategoriaBarema.ativo == True,
                )
                .first()
            )

        if barema_categoria and barema_categoria.criterios:
            baremas_por_categoria[categoria] = barema_categoria.criterios

    criterios_unicos = sorted(set(c.criterio_id for c in criterios_avaliacoes))

    estatisticas = {}
    for categoria in categorias:
        avaliacoes_categoria = [av for av in avaliacoes if av.categoria == categoria]
        notas = [av.nota_final for av in avaliacoes_categoria if av.nota_final is not None]
        estatisticas[categoria] = {
            'total_avaliacoes': len(avaliacoes_categoria),
            'nota_media': round(sum(notas) / len(notas), 2) if notas else 0,
            'nota_maxima': max(notas) if notas else 0,
            'nota_minima': min(notas) if notas else 0,
            'avaliacoes': avaliacoes_categoria[:10],
        }

    estatisticas_criterios_por_categoria = {}
    for categoria in categorias:
        estatisticas_criterios_por_categoria[categoria] = {}
        criterios_categoria = baremas_por_categoria.get(categoria, {})
        for criterio_key, criterio_dados in criterios_categoria.items():
            criterios_do_criterio = [
                c for c in criterios_avaliacoes
                if c.criterio_id == criterio_key and c.avaliacao.categoria == categoria
            ]
            notas_criterio = [c.nota for c in criterios_do_criterio if c.nota is not None]
            estatisticas_criterios_por_categoria[categoria][criterio_key] = {
                'nome': criterio_dados.get('nome', criterio_key),
                'descricao': criterio_dados.get('descricao', ''),
                'pontuacao_max': criterio_dados.get('pontuacao_max', 10),
                'total_avaliacoes': len(criterios_do_criterio),
                'nota_media': round(sum(notas_criterio) / len(notas_criterio), 2) if notas_criterio else 0,
                'nota_maxima': max(notas_criterio) if notas_criterio else 0,
                'nota_minima': min(notas_criterio) if notas_criterio else 0,
                'distribuicao_notas': {
                    '0-2': len([n for n in notas_criterio if 0 <= n <= 2]),
                    '3-5': len([n for n in notas_criterio if 3 <= n <= 5]),
                    '6-8': len([n for n in notas_criterio if 6 <= n <= 8]),
                    '9-10': len([n for n in notas_criterio if 9 <= n <= 10]),
                },
            }

    estatisticas_criterios = {}
    for criterio_id in criterios_unicos:
        criterios_do_criterio = [c for c in criterios_avaliacoes if c.criterio_id == criterio_id]
        notas_criterio = [c.nota for c in criterios_do_criterio if c.nota is not None]
        estatisticas_criterios[criterio_id] = {
            'total_avaliacoes': len(criterios_do_criterio),
            'nota_media': round(sum(notas_criterio) / len(notas_criterio), 2) if notas_criterio else 0,
            'nota_maxima': max(notas_criterio) if notas_criterio else 0,
            'nota_minima': min(notas_criterio) if notas_criterio else 0,
            'distribuicao_notas': {
                '0-2': len([n for n in notas_criterio if 0 <= n <= 2]),
                '3-5': len([n for n in notas_criterio if 3 <= n <= 5]),
                '6-8': len([n for n in notas_criterio if 6 <= n <= 8]),
                '9-10': len([n for n in notas_criterio if 9 <= n <= 10]),
            },
        }

    dados_grafico = {
        'categorias': list(estatisticas.keys()),
        'total_avaliacoes': [estatisticas[cat]['total_avaliacoes'] for cat in categorias],
        'notas_medias': [estatisticas[cat]['nota_media'] for cat in categorias],
    }

    dados_grafico_criterios = {
        'criterios': criterios_unicos,
        'notas_medias_criterios': [estatisticas_criterios.get(c, {}).get('nota_media', 0) for c in criterios_unicos],
    }

    # Construir relatório descritivo por trabalho
    relatorios_trabalhos_map = {}
    for avaliacao in avaliacoes:
        criterios_formatados = []
        for criterio in avaliacao.criterios_avaliacao:
            if criterio_filtro and criterio.criterio_id != criterio_filtro:
                continue
            criterio_info = baremas_por_categoria.get(avaliacao.categoria, {}).get(criterio.criterio_id, {})
            criterios_formatados.append({
                'id': criterio.criterio_id,
                'nome': criterio_info.get('nome', criterio.criterio_id),
                'nota': criterio.nota,
                'observacao': criterio.observacao or '',
            })

        if criterio_filtro and not criterios_formatados:
            continue

        submission = avaliacao.trabalho
        if not submission:
            continue

        trabalho_entry = relatorios_trabalhos_map.setdefault(
            submission.id,
            {
                'trabalho_id': submission.id,
                'titulo': submission.title or f'Trabalho {submission.id}',
                'categoria': avaliacao.categoria,
                'codigo': getattr(submission, 'locator', ''),
                'avaliacoes': [],
                'notas_finais': [],
            },
        )

        revisor_nome = avaliacao.nome_revisor
        if not revisor_nome and avaliacao.revisor:
            revisor_nome = avaliacao.revisor.nome
        alias = revisor_nome or f"Revisor {len(trabalho_entry['avaliacoes']) + 1}"
        revisor_email = avaliacao.revisor.email if getattr(avaliacao, 'revisor', None) else ''
        revisor_id = avaliacao.revisor_id if getattr(avaliacao, 'revisor_id', None) else None

        assignment_info = assignment_lookup.get((submission.id, revisor_id)) if revisor_id else None
        is_reevaluation = bool(getattr(assignment_info, 'is_reevaluation', False))

        nota_final = avaliacao.nota_final if avaliacao.nota_final is not None else None
        if nota_final is not None:
            trabalho_entry['notas_finais'].append(nota_final)

        trabalho_entry['avaliacoes'].append({
            'alias': alias,
            'revisor_nome_exibicao': alias,
            'revisor_email': revisor_email,
            'revisor_id': revisor_id,
            'nota_final': nota_final,
            'data_avaliacao': avaliacao.data_avaliacao.strftime('%d/%m/%Y %H:%M') if avaliacao.data_avaliacao else '',
            'is_reevaluation': is_reevaluation,
            'criterios': criterios_formatados,
        })

    todas_notas_finais: list[float] = []
    resumo_revisores: dict[tuple[int | None, str | None], dict] = {}

    relatorios_trabalhos = []
    for trabalho in relatorios_trabalhos_map.values():
        notas = trabalho.pop('notas_finais')
        trabalho['total_avaliacoes'] = len(trabalho['avaliacoes'])
        if notas:
            trabalho['nota_media'] = round(sum(notas) / len(notas), 2)
            trabalho['nota_maxima'] = max(notas)
            trabalho['nota_minima'] = min(notas)
            todas_notas_finais.extend(notas)
        else:
            trabalho['nota_media'] = 0
            trabalho['nota_maxima'] = 0
            trabalho['nota_minima'] = 0
        relatorios_trabalhos.append(trabalho)

    relatorios_trabalhos.sort(key=lambda item: item['titulo'].lower())

    for trabalho in relatorios_trabalhos:
        for avaliacao in trabalho['avaliacoes']:
            revisor_nome = avaliacao.get('revisor_nome_exibicao')
            revisor_email = avaliacao.get('revisor_email')
            revisor_id = avaliacao.get('revisor_id')
            key = (revisor_id, revisor_email or revisor_nome)
            resumo = resumo_revisores.setdefault(key, {
                'revisor_id': revisor_id,
                'nome': revisor_nome or 'Revisor desconhecido',
                'email': revisor_email or '',
                'total_trabalhos': 0,
                'notas_finais': [],
                'reavaliacoes': 0,
            })
            resumo['total_trabalhos'] += 1
            nota_final = avaliacao.get('nota_final')
            if nota_final is not None:
                resumo['notas_finais'].append(nota_final)
            if is_reevaluation:
                resumo['reavaliacoes'] += 1

    resumo_revisores_list = []
    for item in resumo_revisores.values():
        notas_revisor = item.pop('notas_finais')
        if notas_revisor:
            item['nota_media'] = round(sum(notas_revisor) / len(notas_revisor), 2)
        else:
            item['nota_media'] = 0
        resumo_revisores_list.append(item)

    resumo_revisores_list.sort(key=lambda entry: entry['nome'].lower())

    total_avaliacoes_global = len(todas_notas_finais)
    nota_media_global = (
        round(sum(todas_notas_finais) / total_avaliacoes_global, 2)
        if total_avaliacoes_global
        else 0
    )

    return {
        'estatisticas': estatisticas,
        'estatisticas_criterios': estatisticas_criterios,
        'estatisticas_criterios_por_categoria': estatisticas_criterios_por_categoria,
        'baremas_por_categoria': baremas_por_categoria,
        'dados_grafico': dados_grafico,
        'dados_grafico_criterios': dados_grafico_criterios,
        'categorias': categorias,
        'criterios_unicos': criterios_unicos,
        'relatorios_trabalhos': relatorios_trabalhos,
        'cliente_id_base': cliente_id_base,
        'nota_media_global': nota_media_global,
        'total_avaliacoes_global': total_avaliacoes_global,
        'resumo_revisores': resumo_revisores_list,
    }


@dashboard_routes.route('/metricas_baremas')
@login_required
def metricas_baremas():
    """Página de métricas das respostas dos baremas por trabalho/categoria."""
    if current_user.tipo not in ('cliente', 'admin'):
        return redirect(url_for(endpoints.DASHBOARD))

    categoria_filtro = request.args.get('categoria', '')
    periodo_inicio = request.args.get('periodo_inicio', '')
    periodo_fim = request.args.get('periodo_fim', '')
    criterio_filtro = request.args.get('criterio', '')
    cliente_id_param = request.args.get('cliente_id', type=int)

    dados = _coletar_metricas_baremas_dados(
        current_user,
        categoria_filtro=categoria_filtro,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        criterio_filtro=criterio_filtro,
        cliente_id_override=cliente_id_param,
    )

    return render_template(
        'dashboard/metricas_baremas.html',
        categoria_filtro=categoria_filtro,
        criterio_filtro=criterio_filtro,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        cliente_id_atual=dados['cliente_id_base'],
        **dados,
    )


@dashboard_routes.route('/metricas_baremas/export/<string:formato>')
@login_required
def exportar_metricas_baremas(formato):
    if current_user.tipo not in ('cliente', 'admin'):
        abort(403)

    categoria_filtro = request.args.get('categoria', '')
    periodo_inicio = request.args.get('periodo_inicio', '')
    periodo_fim = request.args.get('periodo_fim', '')
    criterio_filtro = request.args.get('criterio', '')
    cliente_id_param = request.args.get('cliente_id', type=int)

    dados = _coletar_metricas_baremas_dados(
        current_user,
        categoria_filtro=categoria_filtro,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        criterio_filtro=criterio_filtro,
        cliente_id_override=cliente_id_param,
    )

    filtros = {
        'categoria': categoria_filtro or 'Todas',
        'criterio': criterio_filtro or 'Todos',
        'periodo_inicio': periodo_inicio,
        'periodo_fim': periodo_fim,
    }

    if formato.lower() == 'xlsx':
        return _exportar_metricas_baremas_xlsx(dados, filtros)
    if formato.lower() == 'pdf':
        return _exportar_metricas_baremas_pdf(dados, filtros)

    abort(400)


def _exportar_metricas_baremas_xlsx(dados, filtros):
    try:
        import xlsxwriter
    except ImportError as exc:
        abort(500, description=f'Biblioteca XLSX ausente: {exc}')

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    header_format = workbook.add_format({'bold': True, 'bg_color': '#1d4ed8', 'font_color': 'white'})
    wrap_format = workbook.add_format({'text_wrap': True})

    resumo_ws = workbook.add_worksheet('Resumo')
    resumo_headers = ['ID', 'Título', 'Categoria', 'Avaliações', 'Nota Média', 'Nota Máxima', 'Nota Mínima']
    for col, header in enumerate(resumo_headers):
        resumo_ws.write(0, col, header, header_format)

    for row, rel in enumerate(dados['relatorios_trabalhos'], start=1):
        resumo_ws.write(row, 0, rel['trabalho_id'])
        resumo_ws.write(row, 1, rel['titulo'])
        resumo_ws.write(row, 2, rel['categoria'])
        resumo_ws.write(row, 3, rel['total_avaliacoes'])
        resumo_ws.write(row, 4, rel['nota_media'])
        resumo_ws.write(row, 5, rel['nota_maxima'])
        resumo_ws.write(row, 6, rel['nota_minima'])

    resumo_ws.set_column(0, 0, 12)
    resumo_ws.set_column(1, 1, 40)
    resumo_ws.set_column(2, 2, 20)

    footer_row = len(dados['relatorios_trabalhos']) + 1
    if footer_row > 1:
        resumo_ws.write(footer_row, 0, 'Média Geral', header_format)
        resumo_ws.write(footer_row, 1, '')
        resumo_ws.write(footer_row, 2, '')
        resumo_ws.write(footer_row, 3, dados['total_avaliacoes_global'])
        resumo_ws.write(footer_row, 4, dados['nota_media_global'])
        resumo_ws.write(footer_row, 5, '')
        resumo_ws.write(footer_row, 6, '')

    detalhado_ws = workbook.add_worksheet('Avaliações')
    detalhado_headers = [
        'Trabalho ID', 'Título', 'Categoria', 'Revisor', 'E-mail', 'Reavaliação?', 'Data Avaliação', 'Nota Final',
        'Critério', 'Nota Critério', 'Observação'
    ]
    for col, header in enumerate(detalhado_headers):
        detalhado_ws.write(0, col, header, header_format)

    detalhado_ws.set_column(0, 0, 12)
    detalhado_ws.set_column(1, 1, 40)
    detalhado_ws.set_column(2, 2, 20)
    detalhado_ws.set_column(3, 4, 18)
    detalhado_ws.set_column(5, 5, 14)
    detalhado_ws.set_column(6, 7, 15)
    detalhado_ws.set_column(8, 8, 30)
    detalhado_ws.set_column(10, 10, 50)

    row = 1
    for rel in dados['relatorios_trabalhos']:
        for avaliacao in rel['avaliacoes']:
            criterios = avaliacao['criterios'] or [{}]
            for criterio in criterios:
                detalhado_ws.write(row, 0, rel['trabalho_id'])
                detalhado_ws.write(row, 1, rel['titulo'])
                detalhado_ws.write(row, 2, rel['categoria'])
                detalhado_ws.write(row, 3, avaliacao.get('revisor_nome_exibicao', avaliacao['alias']))
                detalhado_ws.write(row, 4, avaliacao.get('revisor_email', ''))
                detalhado_ws.write(row, 5, 'Sim' if avaliacao.get('is_reevaluation') else 'Não')
                detalhado_ws.write(row, 6, avaliacao['data_avaliacao'])
                detalhado_ws.write(row, 7, avaliacao['nota_final'] if avaliacao['nota_final'] is not None else '')
                detalhado_ws.write(row, 8, criterio.get('nome', ''))
                detalhado_ws.write(row, 9, criterio.get('nota', ''))
                detalhado_ws.write(row, 10, criterio.get('observacao', ''), wrap_format)
                row += 1

    workbook.close()
    output.seek(0)

    filename = f"metricas_baremas_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


def _exportar_metricas_baremas_pdf(dados, filtros):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title='Relatório de Métricas dos Baremas',
    )

    styles = getSampleStyleSheet()
    elements = []

    header = styles['Heading1']
    header.alignment = 1
    elements.append(Paragraph('Relatório de Métricas dos Baremas', header))
    elements.append(Spacer(1, 12))

    filtros_texto = f"Categoria: {filtros['categoria']} | Critério: {filtros['criterio']}"
    if filtros.get('periodo_inicio') or filtros.get('periodo_fim'):
        filtros_texto += f" | Período: {filtros.get('periodo_inicio') or '-'} a {filtros.get('periodo_fim') or '-'}"
    elements.append(Paragraph(filtros_texto, styles['Normal']))
    elements.append(Spacer(1, 18))

    for idx, rel in enumerate(dados['relatorios_trabalhos']):
        elements.append(Paragraph(f"Trabalho #{rel['trabalho_id']} - {rel['titulo']}", styles['Heading2']))
        info_table = Table([
            ['Categoria', rel['categoria'], 'Avaliações', rel['total_avaliacoes']],
            ['Nota média', rel['nota_media'], 'Nota máxima', rel['nota_maxima']],
            ['Nota mínima', rel['nota_minima'], '', ''],
        ], colWidths=[90, 180, 90, 120])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 10))

        for avaliacao in rel['avaliacoes']:
            nome_revisor = avaliacao.get('revisor_nome_exibicao', avaliacao['alias'])
            elements.append(Paragraph(
                f"{nome_revisor} - Nota final: {avaliacao['nota_final'] if avaliacao['nota_final'] is not None else 'N/A'}", styles['Heading4']
            ))
            detalhes_revisor = [f"Data da avaliação: {avaliacao['data_avaliacao'] or '-'}"]
            if avaliacao.get('revisor_email'):
                detalhes_revisor.append(f"E-mail: {avaliacao['revisor_email']}")
            elements.append(Paragraph(' | '.join(detalhes_revisor), styles['Normal']))

            if avaliacao['criterios']:
                criterio_data = [['Critério', 'Nota', 'Observações']]
                for criterio in avaliacao['criterios']:
                    criterio_data.append([
                        criterio.get('nome', ''),
                        criterio.get('nota', ''),
                        criterio.get('observacao', ''),
                    ])
                criterio_table = Table(criterio_data, colWidths=[200, 50, 220])
                criterio_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1d4ed8')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOX', (0, 0), (-1, -1), 0.25, colors.grey),
                    ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                elements.append(criterio_table)
            else:
                elements.append(Paragraph('Sem critérios registrados para esta avaliação.', styles['Italic']))

            elements.append(Spacer(1, 8))

        if idx < len(dados['relatorios_trabalhos']) - 1:
            elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)

    filename = f"metricas_baremas_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf',
    )


@dashboard_routes.route('/metricas_baremas/export_revisores/<string:formato>')
@login_required
def exportar_metricas_revisores(formato):
    if current_user.tipo not in ('cliente', 'admin'):
        abort(403)

    categoria_filtro = request.args.get('categoria', '')
    periodo_inicio = request.args.get('periodo_inicio', '')
    periodo_fim = request.args.get('periodo_fim', '')
    criterio_filtro = request.args.get('criterio', '')
    cliente_id_param = request.args.get('cliente_id', type=int)

    dados = _coletar_metricas_baremas_dados(
        current_user,
        categoria_filtro=categoria_filtro,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        criterio_filtro=criterio_filtro,
        cliente_id_override=cliente_id_param,
    )

    filtros = {
        'categoria': categoria_filtro or 'Todas',
        'criterio': criterio_filtro or 'Todos',
        'periodo_inicio': periodo_inicio,
        'periodo_fim': periodo_fim,
    }

    if formato.lower() == 'xlsx':
        return _exportar_revisores_metricas_xlsx(dados, filtros)
    if formato.lower() == 'pdf':
        return _exportar_revisores_metricas_pdf(dados, filtros)

    abort(400)


def _exportar_revisores_metricas_xlsx(dados, filtros):
    try:
        import xlsxwriter
    except ImportError as exc:
        abort(500, description=f'Biblioteca XLSX ausente: {exc}')

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    header_format = workbook.add_format({'bold': True, 'bg_color': '#0f172a', 'font_color': 'white'})
    wrap_format = workbook.add_format({'text_wrap': True})

    por_trabalho_ws = workbook.add_worksheet('Revisores por Trabalho')
    headers = ['Trabalho ID', 'Título', 'Categoria', 'Revisor', 'E-mail', 'Reavaliação?', 'Data Avaliação', 'Nota Final']
    for col, header in enumerate(headers):
        por_trabalho_ws.write(0, col, header, header_format)

    por_trabalho_ws.set_column(0, 0, 12)
    por_trabalho_ws.set_column(1, 1, 45)
    por_trabalho_ws.set_column(2, 2, 22)
    por_trabalho_ws.set_column(3, 4, 28)
    por_trabalho_ws.set_column(5, 5, 16)
    por_trabalho_ws.set_column(6, 7, 16)

    row = 1
    for rel in dados['relatorios_trabalhos']:
        for avaliacao in rel['avaliacoes']:
            nota_final = avaliacao.get('nota_final')
            por_trabalho_ws.write(row, 0, rel['trabalho_id'])
            por_trabalho_ws.write(row, 1, rel['titulo'])
            por_trabalho_ws.write(row, 2, rel['categoria'])
            por_trabalho_ws.write(row, 3, avaliacao.get('revisor_nome_exibicao', avaliacao['alias']))
            por_trabalho_ws.write(row, 4, avaliacao.get('revisor_email', ''))
            por_trabalho_ws.write(row, 5, 'Sim' if avaliacao.get('is_reevaluation') else 'Não')
            por_trabalho_ws.write(row, 6, avaliacao.get('data_avaliacao', ''))
            por_trabalho_ws.write(row, 7, nota_final if nota_final is not None else '')
            row += 1

    resumo_ws = workbook.add_worksheet('Resumo Revisores')
    resumo_headers = ['Revisor', 'E-mail', 'Total Trabalhos', 'Reavaliações', 'Nota Média']
    for col, header in enumerate(resumo_headers):
        resumo_ws.write(0, col, header, header_format)

    resumo_ws.set_column(0, 1, 35)
    resumo_ws.set_column(2, 3, 18)
    resumo_ws.set_column(4, 4, 18)

    for idx, resumo in enumerate(dados['resumo_revisores'], start=1):
        resumo_ws.write(idx, 0, resumo['nome'])
        resumo_ws.write(idx, 1, resumo['email'])
        resumo_ws.write(idx, 2, resumo['total_trabalhos'])
        resumo_ws.write(idx, 3, resumo.get('reavaliacoes', 0))
        resumo_ws.write(idx, 4, resumo['nota_media'])

    filtros_ws = workbook.add_worksheet('Filtros Aplicados')
    filtros_ws.write(0, 0, 'Categoria', header_format)
    filtros_ws.write(0, 1, filtros['categoria'])
    filtros_ws.write(1, 0, 'Critério', header_format)
    filtros_ws.write(1, 1, filtros['criterio'])
    filtros_ws.write(2, 0, 'Período Início', header_format)
    filtros_ws.write(2, 1, filtros.get('periodo_inicio') or '-')
    filtros_ws.write(3, 0, 'Período Fim', header_format)
    filtros_ws.write(3, 1, filtros.get('periodo_fim') or '-')
    filtros_ws.set_column(0, 0, 20)
    filtros_ws.set_column(1, 1, 35, wrap_format)

    workbook.close()
    output.seek(0)

    filename = f"revisores_baremas_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


def _exportar_revisores_metricas_pdf(dados, filtros):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title='Relatório de Revisores por Trabalho',
    )

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph('Revisores por Trabalho', styles['Heading1']))
    elements.append(Spacer(1, 12))

    filtros_texto = f"Categoria: {filtros['categoria']} | Critério: {filtros['criterio']}"
    if filtros.get('periodo_inicio') or filtros.get('periodo_fim'):
        filtros_texto += f" | Período: {filtros.get('periodo_inicio') or '-'} a {filtros.get('periodo_fim') or '-'}"
    elements.append(Paragraph(filtros_texto, styles['Normal']))
    elements.append(Spacer(1, 16))

    if dados['resumo_revisores']:
        resumo_table_data = [['Revisor', 'E-mail', 'Total Trabalhos', 'Reavaliações', 'Nota Média']]
        for resumo in dados['resumo_revisores']:
            resumo_table_data.append([
                resumo['nome'],
                resumo['email'] or '-',
                resumo['total_trabalhos'],
                resumo.get('reavaliacoes', 0),
                resumo['nota_media'],
            ])
        resumo_table = Table(resumo_table_data, colWidths=[150, 150, 70, 70, 60])
        resumo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ]))
        elements.append(Paragraph('Resumo por Revisor', styles['Heading2']))
        elements.append(resumo_table)
        elements.append(Spacer(1, 18))

    for idx, rel in enumerate(dados['relatorios_trabalhos']):
        elements.append(Paragraph(f"Trabalho #{rel['trabalho_id']} - {rel['titulo']}", styles['Heading2']))
        tabela_data = [['Revisor', 'E-mail', 'Reavaliação?', 'Data Avaliação', 'Nota Final']]
        for avaliacao in rel['avaliacoes']:
            tabela_data.append([
                avaliacao.get('revisor_nome_exibicao', avaliacao['alias']),
                avaliacao.get('revisor_email', '-') or '-',
                'Sim' if avaliacao.get('is_reevaluation') else 'Não',
                avaliacao.get('data_avaliacao', '-') or '-',
                avaliacao.get('nota_final', '-') if avaliacao.get('nota_final') is not None else '-',
            ])

        tabela = Table(tabela_data, colWidths=[150, 140, 70, 80, 60])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1d4ed8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.grey),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(tabela)
        elements.append(Spacer(1, 14))

        if idx < len(dados['relatorios_trabalhos']) - 1:
            elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)

    filename = f"revisores_baremas_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf',
    )
