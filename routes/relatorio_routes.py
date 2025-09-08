from flask import Blueprint

relatorio_routes = Blueprint("relatorio_routes", __name__)

from flask import render_template, request, redirect, url_for, flash, send_from_directory, send_file, abort
from flask_login import login_required, current_user
from io import BytesIO
from openpyxl import Workbook
from extensions import db
from utils.auth import log_access_attempt, dashboard_access_required, dashboard_export_required, dashboard_drill_down_required, can_access_dashboard_data, get_dashboard_data_filter
from models import (
    Usuario,
    Evento,
    Oficina,
    OficinaDia,
    Inscricao,
    Feedback,
    LoteTipoInscricao,
    EventoInscricaoTipo,
    Ministrante,
    Checkin,
    Sorteio,
    Cliente,
    Pagamento,
    CertificadoTemplate
)
from models.event import ParticipanteEvento
from models.user import Ministrante
from datetime import datetime
import os

from services.ia_service import gerar_texto_relatorio


def montar_relatorio_mensagem(incluir_financeiro=False):
    from sqlalchemy import func
    
    # Se quiser só as oficinas do cliente, verifique se current_user é admin ou cliente:
    is_admin = (current_user.tipo == 'admin')
    if is_admin:
        total_oficinas = Oficina.query.count()
        # Buscar todas as oficinas para calcular o total de vagas considerando o tipo_inscricao
        oficinas = Oficina.query.options(db.joinedload(Oficina.inscritos)).all()
        total_inscricoes = Inscricao.query.count()
        eventos = Evento.query.all()
    else:
        total_oficinas = Oficina.query.filter_by(cliente_id=current_user.id).count()
        # Buscar oficinas do cliente para calcular o total de vagas considerando o tipo_inscricao
        oficinas = Oficina.query.filter_by(cliente_id=current_user.id).options(db.joinedload(Oficina.inscritos)).all()
        total_inscricoes = Inscricao.query.join(Oficina).filter(Oficina.cliente_id == current_user.id).count()
        eventos = Evento.query.filter_by(cliente_id=current_user.id).all()

    financeiro_por_evento = {}
    if incluir_financeiro:
        inscricoes_q = (
            Inscricao.query.join(Evento)
            .filter(Inscricao.status_pagamento == 'approved')
        )
        if not is_admin:
            inscricoes_q = inscricoes_q.filter(Evento.cliente_id == current_user.id)
        inscricoes = inscricoes_q.options(db.joinedload(Inscricao.evento)).all()

        for ins in inscricoes:
            evento = ins.evento
            if not evento:
                continue
            valor = 0.0
            if ins.lote_id and evento.habilitar_lotes:
                lti = LoteTipoInscricao.query.filter_by(
                    lote_id=ins.lote_id,
                    tipo_inscricao_id=ins.tipo_inscricao_id,
                ).first()
                if lti:
                    valor = float(lti.preco)
            else:
                eit = EventoInscricaoTipo.query.get(ins.tipo_inscricao_id)
                if eit:
                    valor = float(eit.preco)

            financeiro_por_evento[evento.id] = financeiro_por_evento.get(evento.id, 0.0) + valor
    
    # Novo cálculo do total_vagas conforme solicitado:
    # 1. Soma as vagas das oficinas com tipo_inscricao 'com_inscricao_com_limite'
    # 2. Soma o número de inscritos nas oficinas com tipo_inscricao 'com_inscricao_sem_limite'
    total_vagas = 0
    for of in oficinas:
        if of.tipo_inscricao == 'com_inscricao_com_limite':
            total_vagas += of.vagas
        elif of.tipo_inscricao == 'com_inscricao_sem_limite':
            total_vagas += len(of.inscritos)
    
    # Cálculo de adesão
    percentual_adesao = (total_inscricoes / total_vagas) * 100 if total_vagas > 0 else 0

    # Monta a mensagem com emojis e loop
    total_eventos = len(eventos)
    mensagem = (
        "📊 *Relatório do Sistema*\n\n"
        f"✅ *Total de Eventos:* {total_eventos}\n"
        f"✅ *Total de Oficinas:* {total_oficinas}\n"
        f"✅ *Vagas Ofertadas:* {total_vagas}\n"
        f"✅ *Vagas Preenchidas:* {total_inscricoes}\n"
        f"✅ *% de Adesão:* {percentual_adesao:.2f}%\n\n"
        "----------------------------------------\n"
    )
    
    # Agrupar oficinas por evento
    for evento in eventos:
        # Buscar oficinas deste evento
        if is_admin:
            oficinas_evento = Oficina.query.filter_by(evento_id=evento.id).all()
        else:
            oficinas_evento = Oficina.query.filter_by(evento_id=evento.id, cliente_id=current_user.id).all()
        
        # Se não houver oficinas neste evento, pular
        if not oficinas_evento:
            continue
            
        # Adicionar cabeçalho do evento
        mensagem += f"\n🎪 *EVENTO: {evento.nome}*\n"
        mensagem += f"📌 *Total de Oficinas no Evento:* {len(oficinas_evento)}\n"
        if incluir_financeiro:
            receita = financeiro_por_evento.get(evento.id, 0.0)
            mensagem += f"💰 *Receita:* R$ {receita:.2f}\n"
        
        # Adicionar dados de cada oficina do evento
        for oficina in oficinas_evento:
            # Conta inscritos
            num_inscritos = Inscricao.query.filter_by(oficina_id=oficina.id).count()
            
            # Calcula ocupação considerando o tipo de inscrição
            if oficina.tipo_inscricao == 'sem_inscricao':
                ocupacao = 0  # Não é relevante calcular ocupação
                vagas_texto = "N/A (sem inscrição)"
            elif oficina.tipo_inscricao == 'com_inscricao_sem_limite':
                ocupacao = 100  # Sempre 100% pois aceita qualquer número de inscritos
                vagas_texto = "Ilimitadas"
            else:  # com_inscricao_com_limite
                ocupacao = (num_inscritos / oficina.vagas)*100 if oficina.vagas else 0
                vagas_texto = str(oficina.vagas)
            
            # Determina o texto amigável para o tipo de inscrição
            tipo_inscricao_texto = "Sem inscrição"
            if oficina.tipo_inscricao == "com_inscricao_sem_limite":
                tipo_inscricao_texto = "Inscrição sem limite de vagas"
            elif oficina.tipo_inscricao == "com_inscricao_com_limite":
                tipo_inscricao_texto = "Inscrição com vagas limitadas"

            mensagem += (
                f"\n🎓 *Oficina:* {oficina.titulo}\n"
                f"🔹 *Tipo de Inscrição:* {tipo_inscricao_texto}\n"
                f"🔹 *Vagas:* {vagas_texto}\n"
                f"🔹 *Inscritos:* {num_inscritos}\n"
                f"🔹 *Ocupação:* {ocupacao:.2f}%\n"
            )

            mensagem += "----------------------------------------\n"

    return mensagem


@relatorio_routes.route('/relatorio_mensagem')
@login_required
def relatorio_mensagem():
    incluir = request.args.get('financeiro') == '1'
    texto = montar_relatorio_mensagem(incluir)
    return render_template(
        'relatorio/relatorio_mensagem.html',
        texto_relatorio=texto,
        incluir_financeiro=incluir
    )


@relatorio_routes.route('/gerar_relatorio_evento', methods=['GET', 'POST'])
@login_required
@dashboard_access_required
def gerar_relatorio_evento():
    """Dashboard analítico completo de eventos com múltiplas visões e KPIs."""
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_, or_
    import json
    
    # Log de acesso ao dashboard
    log_access_attempt(
        user_id=current_user.id,
        action='dashboard_access',
        resource_type='dashboard',
        resource_id=request.args.get('evento_id'),
        success=True,
        ip_address=request.remote_addr,
        details=f"Visão: {request.args.get('visao', 'executiva')}"
    )
    
    # Controle de acesso
    is_admin = current_user.tipo == 'admin'
    if is_admin:
        eventos = Evento.query.all()
        clientes = Cliente.query.all()
    else:
        eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
        clientes = [current_user] if hasattr(current_user, 'nome') else []
    
    # Obter dados para filtros
    if is_admin:
        oficinas = Oficina.query.all()
        ministrantes = Ministrante.query.all()
    else:
        oficinas = Oficina.query.filter_by(cliente_id=current_user.id).all()
        ministrantes = Ministrante.query.join(Oficina).filter(Oficina.cliente_id==current_user.id).distinct().all()
    
    # Obter dados únicos para filtros
    estados = db.session.query(Evento.estado).distinct().filter(Evento.estado.isnot(None)).all()
    cidades = db.session.query(Evento.cidade).distinct().filter(Evento.cidade.isnot(None)).all()
    modalidades = ['presencial', 'online', 'hibrido']
    turnos = ['manha', 'tarde', 'noite']
    status_opcoes = ['pre_inscricao', 'confirmado', 'cancelado', 'presente']
    tipos_certificado = db.session.query(CertificadoTemplate.tipo).distinct().all()
    
    # Processar filtros
    filtros = {
        'cliente_id': request.args.get('cliente_id', type=int),
        'evento_id': request.args.get('evento_id', type=int),
        'oficina_id': request.args.get('oficina_id', type=int),
        'ministrante_id': request.args.get('ministrante_id', type=int),
        'estado': request.args.get('estado'),
        'cidade': request.args.get('cidade'),
        'turno': request.args.get('turno'),
        'modalidade': request.args.get('modalidade'),
        'status': request.args.get('status'),
        'tipo_inscricao': request.args.get('tipo_inscricao'),
        'pago_gratuito': request.args.get('pago_gratuito'),
        'tipo_certificado': request.args.get('tipo_certificado'),
        'publico_alvo': request.args.get('publico_alvo'),
        'data_inicio': request.args.get('data_inicio'),
        'data_fim': request.args.get('data_fim'),
        'visao': request.args.get('visao', 'executiva')
    }
    
    # Aplicar filtros nas consultas base
    query_inscricoes = Inscricao.query
    query_checkins = Checkin.query
    query_oficinas = Oficina.query
    
    if not is_admin and hasattr(current_user, 'id'):
        query_inscricoes = query_inscricoes.filter(Inscricao.evento_id.in_([e.id for e in eventos]))
        query_checkins = query_checkins.filter(Checkin.evento_id.in_([e.id for e in eventos]))
        query_oficinas = query_oficinas.filter_by(cliente_id=current_user.id)
    
    if filtros['cliente_id']:
        eventos_cliente = [e.id for e in eventos if e.cliente_id == filtros['cliente_id']]
        query_inscricoes = query_inscricoes.filter(Inscricao.evento_id.in_(eventos_cliente))
        query_checkins = query_checkins.filter(Checkin.evento_id.in_(eventos_cliente))
    
    if filtros['evento_id']:
        query_inscricoes = query_inscricoes.filter_by(evento_id=filtros['evento_id'])
        query_checkins = query_checkins.filter_by(evento_id=filtros['evento_id'])
        query_oficinas = query_oficinas.filter_by(evento_id=filtros['evento_id'])
    
    if filtros['oficina_id']:
        query_inscricoes = query_inscricoes.filter_by(oficina_id=filtros['oficina_id'])
        query_checkins = query_checkins.filter_by(oficina_id=filtros['oficina_id'])
    
    if filtros['estado']:
        oficinas_estado = [o.id for o in oficinas if o.estado == filtros['estado']]
        query_inscricoes = query_inscricoes.filter(Inscricao.oficina_id.in_(oficinas_estado))
        query_checkins = query_checkins.filter(Checkin.oficina_id.in_(oficinas_estado))
    
    if filtros['cidade']:
        oficinas_cidade = [o.id for o in oficinas if o.cidade == filtros['cidade']]
        query_inscricoes = query_inscricoes.filter(Inscricao.oficina_id.in_(oficinas_cidade))
        query_checkins = query_checkins.filter(Checkin.oficina_id.in_(oficinas_cidade))
    
    # Calcular KPIs baseados nos filtros aplicados
    kpis = calcular_kpis_dashboard(query_inscricoes, query_checkins, query_oficinas, filtros)
    
    # Dados específicos por visão
    dados_visao = {}
    
    if filtros['visao'] == 'executiva':
        dados_visao = gerar_visao_executiva(query_inscricoes, query_checkins, query_oficinas, filtros)
    elif filtros['visao'] == 'funil':
        dados_visao = gerar_visao_funil(query_inscricoes, query_checkins, filtros)
    elif filtros['visao'] == 'ocupacao':
        dados_visao = gerar_visao_ocupacao(query_oficinas, query_inscricoes, filtros)
    elif filtros['visao'] == 'presenca':
        dados_visao = gerar_visao_presenca(query_checkins, query_inscricoes, filtros)
    elif filtros['visao'] == 'qualidade':
        dados_visao = gerar_visao_qualidade(query_inscricoes, filtros)
    elif filtros['visao'] == 'financeiro':
        dados_visao = gerar_visao_financeiro(query_inscricoes, filtros)
    elif filtros['visao'] == 'certificados':
        dados_visao = gerar_visao_certificados(query_inscricoes, filtros)
    elif filtros['visao'] == 'operacao':
        dados_visao = gerar_visao_operacao(query_checkins, filtros)
    elif filtros['visao'] == 'diversidade':
        dados_visao = gerar_visao_diversidade(query_inscricoes, filtros)
    elif filtros['visao'] == 'geografia':
        dados_visao = gerar_visao_geografia(query_inscricoes, query_oficinas, filtros)
    
    # Exportação de dados
    if request.args.get('export'):
        # Verificar permissão de exportação
        from utils.auth import require_permission
        if not require_permission('dashboard.export'):
            if request.is_json:
                return {'error': 'Acesso negado para exportação'}, 403
            flash('Você não tem permissão para exportar dados do dashboard.', 'error')
            return redirect(url_for('relatorio_routes.gerar_relatorio_evento'))
        
        # Log da exportação
        log_access_attempt(
            user_id=current_user.id,
            action='dashboard_export',
            resource_type='dashboard',
            resource_id=filtros.get('evento_id'),
            success=True,
            ip_address=request.remote_addr,
            details=f"Formato: {request.args.get('export')}, Visão: {filtros['visao']}"
        )
        
        return exportar_dados_dashboard(filtros, kpis, dados_visao, request.args.get('export'))
    
    return render_template(
        'relatorio/dashboard_analitico.html',
        eventos=eventos,
        clientes=clientes,
        oficinas=oficinas,
        ministrantes=ministrantes,
        estados=[e[0] for e in estados],
        cidades=[c[0] for c in cidades],
        modalidades=modalidades,
        turnos=turnos,
        status_opcoes=status_opcoes,
        tipos_certificado=[t[0] for t in tipos_certificado],
        filtros=filtros,
        kpis=kpis,
        dados_visao=dados_visao,
        visao_atual=filtros['visao']
    )


def calcular_kpis_dashboard(query_inscricoes, query_checkins, query_oficinas, filtros):
    """Calcula KPIs executivos para o dashboard."""
    from sqlalchemy import func
    
    # Inscrições totais e únicas
    inscricoes_totais = query_inscricoes.count()
    usuarios_unicos = query_inscricoes.with_entities(Inscricao.usuario_id).distinct().count()
    
    # Check-ins por turno
    checkins_manha = query_checkins.filter(func.time(Checkin.data_hora) < '12:00:00').count()
    checkins_tarde = query_checkins.filter(func.time(Checkin.data_hora) >= '12:00:00').count()
    checkins_total = query_checkins.count()
    
    # Confirmados (status confirmado)
    confirmados = query_inscricoes.filter_by(status='confirmado').count()
    
    # Taxa de presença = presentes / confirmados
    taxa_presenca = (checkins_total / confirmados * 100) if confirmados > 0 else 0
    
    # Capacidade total e usada
    capacidade_total = sum([o.vagas for o in query_oficinas.all()])
    capacidade_usada = (checkins_total / capacidade_total * 100) if capacidade_total > 0 else 0
    
    # No-show = confirmados sem check-in
    no_show = confirmados - checkins_total
    taxa_no_show = (no_show / confirmados * 100) if confirmados > 0 else 0
    
    # Cancelamentos
    cancelamentos = query_inscricoes.filter_by(status='cancelado').count()
    taxa_cancelamento = (cancelamentos / inscricoes_totais * 100) if inscricoes_totais > 0 else 0
    
    # Receita (simulada - implementar com dados reais de pagamento)
    receita_bruta = query_inscricoes.filter_by(status='confirmado').count() * 50  # Valor médio simulado
    receita_liquida = receita_bruta * 0.95  # Descontando taxas
    ticket_medio = receita_liquida / confirmados if confirmados > 0 else 0
    
    # Certificados (simulado)
    certificados_gerados = checkins_total * 0.8  # 80% dos presentes geram certificado
    certificados_baixados = certificados_gerados * 0.6  # 60% fazem download
    taxa_emissao = (certificados_gerados / checkins_total * 100) if checkins_total > 0 else 0
    
    return {
        'inscricoes_totais': inscricoes_totais,
        'usuarios_unicos': usuarios_unicos,
        'checkins_manha': checkins_manha,
        'checkins_tarde': checkins_tarde,
        'checkins_total': checkins_total,
        'confirmados': confirmados,
        'taxa_presenca': round(taxa_presenca, 2),
        'capacidade_total': capacidade_total,
        'capacidade_usada': round(capacidade_usada, 2),
        'no_show': no_show,
        'taxa_no_show': round(taxa_no_show, 2),
        'cancelamentos': cancelamentos,
        'taxa_cancelamento': round(taxa_cancelamento, 2),
        'receita_bruta': receita_bruta,
        'receita_liquida': receita_liquida,
        'ticket_medio': round(ticket_medio, 2),
        'certificados_gerados': int(certificados_gerados),
        'certificados_baixados': int(certificados_baixados),
        'taxa_emissao': round(taxa_emissao, 2)
    }

def gerar_visao_executiva(query_inscricoes, query_checkins, query_oficinas, filtros):
    """Gera dados para a visão executiva (C-level)."""
    from sqlalchemy import func
    
    # Top 5 oficinas por procura
    top_oficinas_procura = db.session.query(
        Oficina.titulo,
        func.count(Inscricao.id).label('inscricoes')
    ).join(Inscricao).group_by(Oficina.id, Oficina.titulo).order_by(func.count(Inscricao.id).desc()).limit(5).all()
    
    # Alertas rápidos
    alertas = []
    oficinas_sobrelotadas = query_oficinas.join(Inscricao).group_by(Oficina.id).having(
        func.count(Inscricao.id) > Oficina.vagas
    ).all()
    
    for oficina in oficinas_sobrelotadas:
        alertas.append(f"Oficina {oficina.titulo} >100% capacidade")
    
    # Satisfação média (simulada)
    satisfacao_media = 4.2
    nps = 65
    
    return {
        'top_oficinas_procura': top_oficinas_procura,
        'alertas': alertas,
        'satisfacao_media': satisfacao_media,
        'nps': nps,
        'tempo_medio_fila': '3.5 min'  # Simulado
    }

def gerar_visao_funil(query_inscricoes, query_checkins, filtros):
    """Gera dados para o funil de conversão."""
    # Simular dados do funil
    visitantes = 10000  # Simulado
    inscritos = query_inscricoes.count()
    confirmados = query_inscricoes.filter_by(status='confirmado').count()
    pagos = confirmados  # Assumindo que confirmados = pagos
    checkin_1turno = query_checkins.filter(func.time(Checkin.data_hora) < '12:00:00').count()
    checkin_2turno = query_checkins.filter(func.time(Checkin.data_hora) >= '12:00:00').count()
    certificados = int(query_checkins.count() * 0.8)
    downloads = int(certificados * 0.6)
    
    # Calcular conversões
    conv_visitante_inscrito = (inscritos / visitantes * 100) if visitantes > 0 else 0
    conv_inscrito_confirmado = (confirmados / inscritos * 100) if inscritos > 0 else 0
    conv_confirmado_pago = (pagos / confirmados * 100) if confirmados > 0 else 0
    conv_pago_checkin1 = (checkin_1turno / pagos * 100) if pagos > 0 else 0
    conv_checkin1_checkin2 = (checkin_2turno / checkin_1turno * 100) if checkin_1turno > 0 else 0
    conv_checkin_certificado = (certificados / query_checkins.count() * 100) if query_checkins.count() > 0 else 0
    conv_certificado_download = (downloads / certificados * 100) if certificados > 0 else 0
    
    return {
        'funil_dados': {
            'visitantes': visitantes,
            'inscritos': inscritos,
            'confirmados': confirmados,
            'pagos': pagos,
            'checkin_1turno': checkin_1turno,
            'checkin_2turno': checkin_2turno,
            'certificados': certificados,
            'downloads': downloads
        },
        'conversoes': {
            'visitante_inscrito': round(conv_visitante_inscrito, 2),
            'inscrito_confirmado': round(conv_inscrito_confirmado, 2),
            'confirmado_pago': round(conv_confirmado_pago, 2),
            'pago_checkin1': round(conv_pago_checkin1, 2),
            'checkin1_checkin2': round(conv_checkin1_checkin2, 2),
            'checkin_certificado': round(conv_checkin_certificado, 2),
            'certificado_download': round(conv_certificado_download, 2)
        }
    }

def gerar_visao_ocupacao(query_oficinas, query_inscricoes, filtros):
    """Gera dados para ocupação e agenda."""
    from collections import defaultdict
    
    # Ocupação por dia
    ocupacao_por_dia = defaultdict(list)
    
    for oficina in query_oficinas.all():
        for dia in oficina.dias:
            inscricoes_dia = query_inscricoes.filter_by(oficina_id=oficina.id).count()
            ocupacao_pct = (inscricoes_dia / oficina.vagas * 100) if oficina.vagas > 0 else 0
            
            ocupacao_por_dia[str(dia.data)].append({
                'oficina': oficina.titulo,
                'horario': f"{dia.horario_inicio}-{dia.horario_fim}",
                'ocupacao': round(ocupacao_pct, 1),
                'vagas_total': oficina.vagas,
                'vagas_ocupadas': inscricoes_dia
            })
    
    # Gargalos (>85% ocupação)
    gargalos = []
    for data, oficinas_dia in ocupacao_por_dia.items():
        for oficina_info in oficinas_dia:
            if oficina_info['ocupacao'] > 85:
                gargalos.append({
                    'data': data,
                    'oficina': oficina_info['oficina'],
                    'ocupacao': oficina_info['ocupacao']
                })
    
    return {
        'ocupacao_por_dia': dict(ocupacao_por_dia),
        'gargalos': gargalos
    }

def gerar_visao_presenca(query_checkins, query_inscricoes, filtros):
    """Gera dados para presença e frequência."""
    from sqlalchemy import func
    
    # Taxa de presença por oficina
    presenca_por_oficina = db.session.query(
        Oficina.titulo,
        func.count(Inscricao.id).label('confirmados'),
        func.count(Checkin.id).label('presentes')
    ).outerjoin(Inscricao).outerjoin(Checkin, Checkin.inscricao_id == Inscricao.id).group_by(Oficina.id, Oficina.titulo).all()
    
    # Calcular taxa de presença
    dados_presenca = []
    for oficina, confirmados, presentes in presenca_por_oficina:
        taxa = (presentes / confirmados * 100) if confirmados > 0 else 0
        dados_presenca.append({
            'oficina': oficina,
            'confirmados': confirmados,
            'presentes': presentes,
            'taxa_presenca': round(taxa, 2)
        })
    
    return {
        'presenca_por_oficina': dados_presenca,
        'reincidencia_faltas': 15,  # Simulado
        'retencao_30_dias': 78,  # Simulado
        'retencao_60_dias': 65,  # Simulado
        'retencao_90_dias': 52   # Simulado
    }

def gerar_visao_qualidade(query_inscricoes, filtros):
    """Gera dados para qualidade e feedback."""
    # Dados simulados de feedback
    return {
        'nota_media_geral': 4.3,
        'nps_geral': 68,
        'feedback_por_categoria': {
            'conteudo': 4.5,
            'logistica': 4.1,
            'estrutura': 4.0,
            'material': 4.2
        },
        'comentarios_positivos': 85,
        'comentarios_negativos': 15,
        'principais_elogios': ['Conteúdo excelente', 'Instrutor preparado', 'Material didático'],
        'principais_criticas': ['Sala pequena', 'Ar condicionado', 'Horário']
    }

def gerar_visao_financeiro(query_inscricoes, filtros):
    """Gera dados financeiros."""
    confirmados = query_inscricoes.filter_by(status='confirmado').count()
    
    # Dados simulados financeiros
    return {
        'receita_total': confirmados * 50,
        'receita_liquida': confirmados * 47.5,
        'taxa_conversao_pagamento': 95.5,
        'ticket_medio': 50.0,
        'inadimplencia': 2.3,
        'chargebacks': 0.8,
        'custo_por_participante': 35.0,
        'margem_liquida': 25.0
    }

def gerar_visao_certificados(query_inscricoes, filtros):
    """Gera dados sobre certificados."""
    checkins = Checkin.query.count()
    
    return {
        'certificados_gerados': int(checkins * 0.8),
        'certificados_baixados': int(checkins * 0.6),
        'taxa_emissao': 80.0,
        'taxa_download': 75.0,
        'tempo_medio_emissao': '2.3 min',
        'erros_renderizacao': 3,
        'certificados_por_tipo': {
            'participacao': int(checkins * 0.7),
            'ministrante': int(checkins * 0.05),
            'avaliador': int(checkins * 0.05)
        }
    }

def gerar_visao_operacao(query_checkins, filtros):
    """Gera dados operacionais e de segurança."""
    total_checkins = query_checkins.count()
    
    return {
        'qr_validos': int(total_checkins * 0.98),
        'qr_invalidos': int(total_checkins * 0.02),
        'tentativas_fraude': 5,
        'checkins_fora_janela': 12,
        'ips_duplicados': 8,
        'logs_auditoria': 156
    }

def gerar_visao_diversidade(query_inscricoes, filtros):
    """Gera dados sobre inclusão e diversidade."""
    total_inscricoes = query_inscricoes.count()
    
    return {
        'distribuicao_genero': {
            'feminino': 60,
            'masculino': 38,
            'outros': 2
        },
        'pcd_atendidos': 15,
        'solicitacoes_acessibilidade': 8,
        'ods_relacionados': ['ODS 4 - Educação', 'ODS 5 - Igualdade de Gênero']
    }

def gerar_visao_geografia(query_inscricoes, query_oficinas, filtros):
    """Gera dados geográficos."""
    from sqlalchemy import func
    
    # Inscrições por cidade
    inscricoes_por_cidade = db.session.query(
        Oficina.cidade,
        Oficina.estado,
        func.count(Inscricao.id).label('inscricoes')
    ).join(Inscricao).group_by(Oficina.cidade, Oficina.estado).all()
    
    dados_geograficos = []
    for cidade, estado, inscricoes in inscricoes_por_cidade:
        dados_geograficos.append({
            'cidade': cidade,
            'estado': estado,
            'inscricoes': inscricoes,
            'receita': inscricoes * 50,  # Simulado
            'satisfacao': 4.2  # Simulado
        })
    
    return {
        'dados_por_cidade': dados_geograficos,
        'ranking_cidades': sorted(dados_geograficos, key=lambda x: x['inscricoes'], reverse=True)[:10]
    }

def exportar_dados_dashboard(filtros, kpis, dados_visao, formato):
    """Exporta dados do dashboard em diferentes formatos."""
    from io import BytesIO
    import json
    
    if formato == 'json':
        dados_export = {
            'filtros': filtros,
            'kpis': kpis,
            'dados_visao': dados_visao,
            'timestamp': datetime.now().isoformat()
        }
        
        buffer = BytesIO()
        buffer.write(json.dumps(dados_export, indent=2, default=str).encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'dashboard_dados_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
            mimetype='application/json'
        )
    
    elif formato == 'csv':
        import csv
        
        buffer = BytesIO()
        output = buffer.getvalue().decode('utf-8')
        
        # Implementar exportação CSV dos KPIs
        csv_data = "Métrica,Valor\n"
        for key, value in kpis.items():
            csv_data += f"{key},{value}\n"
        
        buffer = BytesIO(csv_data.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'dashboard_kpis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mimetype='text/csv'
        )

@relatorio_routes.route('/relatorios/<path:filename>')
@login_required
def get_relatorio_file(filename):
    # Ajuste o caminho para a pasta de relatórios
    pasta_uploads = os.path.join('uploads', 'relatorios')
    return send_from_directory(pasta_uploads, filename)

@relatorio_routes.route('/gerar_modelo/<string:tipo>', methods=['GET'])
@login_required
def gerar_modelo(tipo):
    """
    Gera um arquivo Excel (XLSX) em memória com colunas obrigatórias
    para importação de Usuários ou Oficinas. Retorna o arquivo para download.
    
    Use:
      /gerar_modelo/usuarios  -> para Modelo de Usuários
      /gerar_modelo/oficinas  -> para Modelo de Oficinas
    """
    # 1. Cria o Workbook em memória
    wb = Workbook()
    ws = wb.active

    if tipo.lower() == 'usuarios':
        ws.title = "ModeloUsuarios"

        # Exemplo de colunas do model Usuario:
        #   nome, cpf, email, senha, formacao, tipo
        colunas = [
            "nome", "cpf", "email", "senha", "formacao", "tipo"
        ]
        ws.append(colunas)

        # Exemplo de linha de demonstração
        ws.append([
            "Fulano de Tal",     # nome
            "123.456.789-00",    # cpf
            "fulano@email.com",  # email
            "senha123",          # senha
            "Graduado em X",     # formacao
            "participante"       # tipo: pode ser admin, cliente, participante, etc.
        ])

        # Nome do arquivo para download
        nome_arquivo = "modelo_usuarios.xlsx"

    elif tipo.lower() == 'oficinas':
        ws.title = "ModeloOficinas"

        # Exemplo de colunas do model Oficina (e OficinaDia):
        #   titulo, descricao, ministrante_id, vagas, carga_horaria,
        #   estado, cidade, datas, horarios_inicio, horarios_fim
        colunas = [
            "titulo", "descricao", "ministrante_id",
            "vagas", "carga_horaria", "estado", "cidade",
            "datas", "horarios_inicio", "horarios_fim"
        ]
        ws.append(colunas)

        # Exemplo de linha de demonstração
        ws.append([
            "Oficina Exemplo",              # titulo
            "Descricao da oficina",         # descricao
            1,                              # ministrante_id
            30,                             # vagas
            "4h",                           # carga_horaria
            "SP",                           # estado
            "São Paulo",                    # cidade
            "01/09/2025,02/09/2025",        # datas (separado por vírgula)
            "08:00,08:00",                  # horarios_inicio (mesma quantidade de itens de datas)
            "12:00,12:00"                   # horarios_fim
        ])

        nome_arquivo = "modelo_oficinas.xlsx"

    else:
        # Se não for "usuarios" nem "oficinas", retorna 400 (Bad Request)
        abort(400, "Tipo inválido. Use 'usuarios' ou 'oficinas'.")

    # 2. Salva o Workbook em um buffer de memória
    output = BytesIO()
    wb.save(output)
    output.seek(0)  # Volta para o início do buffer

    # 3. Retorna o arquivo
    return send_file(
        output,
        as_attachment=True,
        download_name=nome_arquivo,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# API Endpoints para Dashboard Analítico
@relatorio_routes.route('/api/dashboard/oficina/<int:oficina_id>', methods=['GET'])
@login_required
@dashboard_drill_down_required
def api_dashboard_oficina_details(oficina_id):
    """API para detalhes de oficina no dashboard."""
    try:
        # Verificar se o usuário pode acessar esta oficina
        if not can_access_dashboard_data(current_user, 'oficina', oficina_id):
            return {'error': 'Acesso negado'}, 403
        
        oficina = Oficina.query.get_or_404(oficina_id)
        
        # Log do acesso
        log_access_attempt(
            user_id=current_user.id,
            action='dashboard_drill_down',
            resource_type='oficina',
            resource_id=oficina_id,
            success=True,
            ip_address=request.remote_addr,
            details='Drill-down oficina details'
        )
        
        # Calcular métricas da oficina
        inscricoes = Inscricao.query.filter_by(oficina_id=oficina_id).all()
        checkins = Checkin.query.filter_by(oficina_id=oficina_id).all()
        
        dados = {
            'info': {
                'id': oficina.id,
                'titulo': oficina.titulo,
                'descricao': oficina.descricao,
                'vagas': oficina.vagas,
                'carga_horaria': oficina.carga_horaria,
                'estado': oficina.estado,
                'cidade': oficina.cidade,
                'modalidade': oficina.modalidade
            },
            'metricas': {
                'total_inscricoes': len(inscricoes),
                'total_presencas': len(checkins),
                'taxa_presenca': (len(checkins) / len(inscricoes) * 100) if inscricoes else 0,
                'ocupacao': (len(inscricoes) / oficina.vagas * 100) if oficina.vagas else 0
            },
            'inscricoes': [{
                'id': i.id,
                'usuario_nome': i.usuario.nome if i.usuario else 'N/A',
                'usuario_email': i.usuario.email if i.usuario else 'N/A',
                'status': i.status,
                'data_inscricao': i.data_inscricao.isoformat() if i.data_inscricao else None
            } for i in inscricoes[:50]]  # Limitar a 50 registros
        }
        
        return dados
        
    except Exception as e:
        log_access_attempt(
            user_id=current_user.id,
            action='dashboard_drill_down',
            resource_type='oficina',
            resource_id=oficina_id,
            success=False,
            ip_address=request.remote_addr,
            details=f'Erro: {str(e)}'
        )
        return {'error': 'Erro interno do servidor'}, 500


@relatorio_routes.route('/api/dashboard/participante/<int:participante_id>', methods=['GET'])
@login_required
@dashboard_drill_down_required
def api_dashboard_participante_details(participante_id):
    """API para detalhes de participante no dashboard."""
    try:
        # Verificar se o usuário pode acessar este participante
        if not can_access_dashboard_data(current_user, 'participante', participante_id):
            return {'error': 'Acesso negado'}, 403
        
        participante = Usuario.query.get_or_404(participante_id)
        
        # Log do acesso
        log_access_attempt(
            user_id=current_user.id,
            action='dashboard_drill_down',
            resource_type='participante',
            resource_id=participante_id,
            success=True,
            ip_address=request.remote_addr,
            details='Drill-down participante details'
        )
        
        # Calcular métricas do participante
        inscricoes = Inscricao.query.filter_by(usuario_id=participante_id).all()
        checkins = Checkin.query.filter_by(usuario_id=participante_id).all()
        
        dados = {
            'info': {
                'id': participante.id,
                'nome': participante.nome,
                'email': participante.email,
                'tipo': participante.tipo,
                'data_cadastro': participante.data_cadastro.isoformat() if participante.data_cadastro else None
            },
            'metricas': {
                'total_inscricoes': len(inscricoes),
                'total_presencas': len(checkins),
                'taxa_presenca': (len(checkins) / len(inscricoes) * 100) if inscricoes else 0
            },
            'inscricoes': [{
                'id': i.id,
                'oficina_titulo': i.oficina.titulo if i.oficina else 'N/A',
                'status': i.status,
                'data_inscricao': i.data_inscricao.isoformat() if i.data_inscricao else None
            } for i in inscricoes[:50]]  # Limitar a 50 registros
        }
        
        return dados
        
    except Exception as e:
        log_access_attempt(
            user_id=current_user.id,
            action='dashboard_drill_down',
            resource_type='participante',
            resource_id=participante_id,
            success=False,
            ip_address=request.remote_addr,
            details=f'Erro: {str(e)}'
        )
        return {'error': 'Erro interno do servidor'}, 500


@relatorio_routes.route('/api/dashboard/evento/<int:evento_id>', methods=['GET'])
@login_required
@dashboard_drill_down_required
def api_dashboard_evento_details(evento_id):
    """API para detalhes de evento no dashboard."""
    try:
        # Verificar se o usuário pode acessar este evento
        if not can_access_dashboard_data(current_user, 'evento', evento_id):
            return {'error': 'Acesso negado'}, 403
        
        evento = Evento.query.get_or_404(evento_id)
        
        # Log do acesso
        log_access_attempt(
            user_id=current_user.id,
            action='dashboard_drill_down',
            resource_type='evento',
            resource_id=evento_id,
            success=True,
            ip_address=request.remote_addr,
            details='Drill-down evento details'
        )
        
        # Calcular métricas do evento
        oficinas = Oficina.query.filter_by(evento_id=evento_id).all()
        inscricoes = Inscricao.query.join(Oficina).filter(Oficina.evento_id == evento_id).all()
        checkins = Checkin.query.filter_by(evento_id=evento_id).all()
        
        dados = {
            'info': {
                'id': evento.id,
                'nome': evento.nome,
                'descricao': evento.descricao,
                'data_inicio': evento.data_inicio.isoformat() if evento.data_inicio else None,
                'data_fim': evento.data_fim.isoformat() if evento.data_fim else None,
                'estado': evento.estado,
                'cidade': evento.cidade,
                'modalidade': evento.modalidade
            },
            'metricas': {
                'total_oficinas': len(oficinas),
                'total_inscricoes': len(inscricoes),
                'total_presencas': len(checkins),
                'taxa_presenca': (len(checkins) / len(inscricoes) * 100) if inscricoes else 0
            },
            'oficinas': [{
                'id': o.id,
                'titulo': o.titulo,
                'vagas': o.vagas,
                'inscricoes': Inscricao.query.filter_by(oficina_id=o.id).count(),
                'presencas': Checkin.query.filter_by(oficina_id=o.id).count()
            } for o in oficinas[:50]]  # Limitar a 50 registros
        }
        
        return dados
        
    except Exception as e:
        log_access_attempt(
            user_id=current_user.id,
            action='dashboard_drill_down',
            resource_type='evento',
            resource_id=evento_id,
            success=False,
            ip_address=request.remote_addr,
            details=f'Erro: {str(e)}'
        )
        return {'error': 'Erro interno do servidor'}, 500


