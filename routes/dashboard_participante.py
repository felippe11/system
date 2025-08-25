from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, session, request
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_
from typing import Optional
import logging
from sqlalchemy.exc import ProgrammingError

logger = logging.getLogger(__name__)

from extensions import db
from models import (
    Evento,
    Oficina,
    OficinaDia,
    ConfiguracaoCliente,
    ConfiguracaoEvento,
    HorarioVisitacao,
    Usuario,
    Formulario,
    RegraInscricaoEvento,
)

dashboard_participante_routes = Blueprint('dashboard_participante_routes', __name__)


@dashboard_participante_routes.route('/dashboard_participante')
@login_required
def dashboard_participante():
    logger.debug("\n======= INICIANDO DASHBOARD PARTICIPANTE =======")
    logger.debug(f"DEBUG [1] -> current_user.id = {current_user.id}, current_user.tipo = {current_user.tipo}")
    
    if current_user.tipo != 'participante':
        logger.debug(f"DEBUG [2] -> Redirecionando: usuário não é participante (tipo: {current_user.tipo})")
        return redirect(url_for('dashboard_routes.dashboard'))

    logger.debug(f"DEBUG [3] -> Usuário é participante, cliente_id = {current_user.cliente_id}")

    # Se o participante está associado a um cliente, buscamos a config desse cliente
    config_cliente = None
    
    # NOVA LOGICA: considerar apenas eventos vinculados ao participante
    logger.debug("DEBUG [4] -> Calculando conjunto de eventos do participante")

    evento_ids = set()
    for insc in current_user.inscricoes:
        if insc.oficina and insc.oficina.evento_id:
            evento_ids.add(insc.oficina.evento_id)
        elif insc.evento_id:
            evento_ids.add(insc.evento_id)

    if current_user.evento_id:
        evento_ids.add(current_user.evento_id)

    logger.debug(f"DEBUG [5] -> Evento IDs coletados: {evento_ids}")

    eventos = Evento.query.filter(Evento.id.in_(evento_ids)).all() if evento_ids else []
    for ev in eventos:
        ev.configuracao_evento = ConfiguracaoEvento.query.filter_by(evento_id=ev.id).first()

    logger.debug(f"DEBUG [6] -> Total de eventos do participante: {len(eventos)}")

    # A seleção de evento será realizada após ordenar e considerar o parâmetro
    evento = None
    formularios_disponiveis = False
    
    if current_user.cliente_id:
        logger.debug(f"DEBUG [11] -> Buscando configuração do cliente_id = {current_user.cliente_id}")
        from models import ConfiguracaoCliente
        config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=current_user.cliente_id).first()
        
        # Se não existir ainda, pode criar com valores padrão
        if not config_cliente:
            logger.debug(f"DEBUG [12] -> Configuração não encontrada, criando padrão para cliente_id = {current_user.cliente_id}")
            config_cliente = ConfiguracaoCliente(
                cliente_id=current_user.cliente_id,
                permitir_checkin_global=False,
                habilitar_feedback=False,
                habilitar_certificado_individual=False
            )
            db.session.add(config_cliente)
            db.session.commit()
            logger.debug(f"DEBUG [13] -> Configuração padrão criada e salva com sucesso")
        else:
            logger.debug(f"DEBUG [14] -> Configuração encontrada para cliente_id = {current_user.cliente_id}")
    
    # CORREÇÃO: Limpar inscrições inválidas (oficina_id = None)
    # Incluir inscrições que possuam somente evento_id
    inscricoes_validas = [
        i for i in current_user.inscricoes
        if i.oficina_id is not None or i.evento_id is not None
    ]
    logger.debug(f"DEBUG [16] -> Filtrando inscrições válidas: {len(current_user.inscricoes)} -> {len(inscricoes_validas)}")
    
    # Obter os eventos em que o participante está inscrito
    logger.debug(f"DEBUG [17] -> Buscando eventos inscritos para participante_id = {current_user.id}")
    eventos_inscritos = []
    for inscricao in inscricoes_validas:
        logger.debug(
            f"DEBUG [18] -> Verificando inscrição: {inscricao.id}, oficina_id: {inscricao.oficina_id}, evento_id: {inscricao.evento_id}"
        )
        if inscricao.oficina and inscricao.oficina.evento_id:
            eventos_inscritos.append(inscricao.oficina.evento_id)
            logger.debug(f"DEBUG [19] -> Adicionado evento_id: {inscricao.oficina.evento_id}")
        elif inscricao.evento_id:
            eventos_inscritos.append(inscricao.evento_id)
            logger.debug(f"DEBUG [19b] -> Adicionado evento_id sem oficina: {inscricao.evento_id}")
    
    # Remover duplicatas
    eventos_inscritos_original = eventos_inscritos.copy()
    eventos_inscritos = list(set(eventos_inscritos))
    logger.debug(f"DEBUG [20] -> Eventos inscritos: {len(eventos_inscritos_original)} -> {len(eventos_inscritos)} (após remover duplicatas)")
    
    # Obter IDs de todos os eventos carregados
    eventos_disponiveis_ids = [e.id for e in eventos] if eventos else []
    logger.debug(f"DEBUG [21] -> IDs de eventos disponíveis: {eventos_disponiveis_ids}")
    
    # CORREÇÃO 2: Verificar se há eventos inscritos que não estão na lista de eventos disponíveis
    eventos_inscritos_ausentes = [e_id for e_id in eventos_inscritos if e_id not in eventos_disponiveis_ids]
    
    if eventos_inscritos_ausentes:
        logger.debug(f"DEBUG [22] -> Eventos inscritos ausentes: {eventos_inscritos_ausentes}, buscando detalhes")
        # Buscar os eventos ausentes
        eventos_ausentes = Evento.query.filter(Evento.id.in_(eventos_inscritos_ausentes)).all()
        # Adicionar aos eventos disponíveis
        eventos.extend(eventos_ausentes)
        # Atualizar lista de IDs
        eventos_disponiveis_ids = [e.id for e in eventos]
        logger.debug(f"DEBUG [23] -> Total de eventos após adicionar ausentes: {len(eventos)}")

    # Ordenar eventos por data_inicio de forma decrescente
    eventos_sorted = sorted(
        eventos,
        key=lambda e: (e.data_inicio or datetime.min),
        reverse=True
    )
    logger.debug(f"DEBUG [23b] -> Ordem final dos eventos: {[e.id for e in eventos_sorted]}")

    # Selecionar evento via parâmetro ou usar o mais recente
    evento_id_param = request.args.get('evento_id', type=int)
    if evento_id_param:
        session['evento_id'] = evento_id_param
    selected_event_id = evento_id_param or session.get('evento_id')
    evento = next((e for e in eventos_sorted if e.id == selected_event_id), None)
    if not evento and eventos_sorted:
        evento = eventos_sorted[0]
        session['evento_id'] = evento.id
    logger.debug(f"DEBUG [8] -> Evento selecionado: {evento.id if evento else None}")

    config_evento = evento.configuracao_evento if evento else None
    permitir_checkin = (
        config_evento.permitir_checkin_global
        if config_evento and config_evento.permitir_checkin_global is not None
        else (config_cliente.permitir_checkin_global if config_cliente else False)
    )
    habilitar_feedback = (
        config_evento.habilitar_feedback
        if config_evento and config_evento.habilitar_feedback is not None
        else (config_cliente.habilitar_feedback if config_cliente else False)
    )
    habilitar_certificado = (
        config_evento.habilitar_certificado_individual
        if config_evento and config_evento.habilitar_certificado_individual is not None
        else (
            config_cliente.habilitar_certificado_individual if config_cliente else False
        )
    )

    logger.debug(
        f"DEBUG [15] -> Configurações evento: checkin={permitir_checkin}, feedback={habilitar_feedback}, certificado={habilitar_certificado}"
    )

    # Verifica se há formulários disponíveis para preenchimento associados ao cliente do participante
    if current_user.cliente_id:
        logger.debug(f"DEBUG [9] -> Verificando formulários disponíveis para cliente_id = {current_user.cliente_id}")
        try:
            form_query = Formulario.query.filter_by(cliente_id=current_user.cliente_id)
            evento_ref = evento.id if evento else current_user.evento_id
            if evento_ref:
                form_query = form_query.join(Formulario.eventos).filter(Evento.id == evento_ref)
            form_count = form_query.count()
            formularios_disponiveis = form_count > 0
            logger.debug(f"DEBUG [10] -> Formulários disponíveis: {formularios_disponiveis} (total: {form_count})")
        except ProgrammingError as e:
            logger.error(f"Erro ao verificar formulários disponíveis: {e}")
            flash("Erro ao carregar formulários disponíveis.", "danger")

    # Combinar todos os IDs de eventos (disponíveis + inscritos) e remover duplicatas
    todos_eventos_ids = list(set(eventos_disponiveis_ids + eventos_inscritos))
    logger.debug(f"DEBUG [24] -> IDs de todos os eventos (disponíveis + inscritos): {todos_eventos_ids}")
    
    # Buscar detalhes de todos os eventos e verificar se já ocorreram
    eventos_info = {}
    data_atual = datetime.now().date()
    logger.debug(f"DEBUG [25] -> Data atual = {data_atual}")
    
    logger.debug(f"DEBUG [26] -> Processando informações de {len(todos_eventos_ids)} eventos")
    for evento_id in todos_eventos_ids:
        logger.debug(f"DEBUG [27] -> Buscando evento_id = {evento_id}")
        evento_obj = Evento.query.get(evento_id)
        if evento_obj:
            logger.debug(f"DEBUG [28] -> Evento {evento_obj.id} - {evento_obj.nome}")
            logger.debug(f"DEBUG [29] -> data_inicio = {evento_obj.data_inicio}, data_fim = {evento_obj.data_fim}")
            
            # CORREÇÃO 3: Um evento só é considerado encerrado se:
            # 1. Tiver uma data_fim definida E
            # 2. A data_fim for anterior à data atual
            ja_ocorreu = False
            
            # Se data_fim for nula, consideramos o evento como não encerrado (aberto)
            if evento_obj.data_fim:
                logger.debug(f"DEBUG [30] -> Processando data_fim para evento_id = {evento_obj.id}")
                # Converter para data se for datetime
                if hasattr(evento_obj.data_fim, 'date'):
                    data_fim = evento_obj.data_fim.date()
                    logger.debug(f"DEBUG [31] -> Convertendo datetime para date: {data_fim}")
                else:
                    # Se já for um objeto date
                    data_fim = evento_obj.data_fim
                    logger.debug(f"DEBUG [32] -> Já é objeto date: {data_fim}")
                
                # Só consideramos encerrado se a data_fim for anterior à data atual
                ja_ocorreu = data_fim < data_atual
                logger.debug(f"DEBUG [33] -> data_fim ({data_fim}) < data_atual ({data_atual})? {ja_ocorreu}")
            else:
                logger.debug(f"DEBUG [34] -> Evento sem data_fim, considerado aberto")
            
            # Verificar se é um evento futuro (data_inicio posterior à data atual)
            eh_futuro = False
            if evento_obj.data_inicio:
                logger.debug(f"DEBUG [35] -> Processando data_inicio para evento_id = {evento_obj.id}")
                if hasattr(evento_obj.data_inicio, 'date'):
                    data_inicio = evento_obj.data_inicio.date()
                    logger.debug(f"DEBUG [36] -> Convertendo datetime para date: {data_inicio}")
                else:
                    data_inicio = evento_obj.data_inicio
                    logger.debug(f"DEBUG [37] -> Já é objeto date: {data_inicio}")
                
                eh_futuro = data_inicio > data_atual
                logger.debug(f"DEBUG [38] -> É evento futuro (data_inicio ({data_inicio}) > data_atual ({data_atual}))? {eh_futuro}")
            else:
                logger.debug(f"DEBUG [39] -> Evento sem data_inicio definida, considerado atual")
            
            # Registrar status e informações do evento
            status = 'Futuro' if eh_futuro else ('Encerrado' if ja_ocorreu else 'Atual')
            eventos_info[evento_id] = {
                'id': evento_obj.id,
                'nome': evento_obj.nome,
                'data_inicio': evento_obj.data_inicio,
                'data_fim': evento_obj.data_fim,
                'ja_ocorreu': ja_ocorreu,
                'eh_futuro': eh_futuro,
                'status': status
            }
            logger.debug(f"DEBUG [40] -> Evento {evento_obj.id} classificado como '{status}'")
    
    # CORREÇÃO 4: Buscar oficinas para cada evento individualmente
    logger.debug(f"DEBUG [41] -> Buscando oficinas para todos os eventos e oficinas sem eventos")
    oficinas = []
    
    # Primeiro, buscar oficinas dos eventos identificados
    if todos_eventos_ids:
        logger.debug(f"DEBUG [42] -> Buscando oficinas para eventos IDs: {todos_eventos_ids}")
        oficinas_eventos = Oficina.query.filter(Oficina.evento_id.in_(todos_eventos_ids)).all()
        oficinas.extend(oficinas_eventos)
        logger.debug(f"DEBUG [43] -> Encontradas {len(oficinas_eventos)} oficinas para os eventos")
    
    # CORREÇÃO 5: Adicionar oficinas sem evento associado (evento_id=None)
    logger.debug(f"DEBUG [44] -> Buscando oficinas sem evento associado")
    if current_user.cliente_id:
        # Buscar oficinas do cliente sem evento associado
        oficinas_sem_evento_cliente = Oficina.query.filter_by(
            cliente_id=current_user.cliente_id, 
            evento_id=None
        ).all()
        oficinas.extend(oficinas_sem_evento_cliente)
        logger.debug(f"DEBUG [45] -> Encontradas {len(oficinas_sem_evento_cliente)} oficinas do cliente sem evento")
    
    # Buscar oficinas globais sem evento associado
    oficinas_sem_evento_globais = Oficina.query.filter_by(
        cliente_id=None, 
        evento_id=None
    ).all()
    oficinas.extend(oficinas_sem_evento_globais)
    logger.debug(f"DEBUG [46] -> Encontradas {len(oficinas_sem_evento_globais)} oficinas globais sem evento")
    
    # CORREÇÃO 6: Se não encontramos oficinas mas temos eventos, buscar todas as oficinas do sistema
    if len(oficinas) == 0 and len(eventos) > 0:
        logger.debug(f"DEBUG [47] -> Não foram encontradas oficinas. Buscando oficinas do cliente")
        if current_user.cliente_id:
            oficinas_cliente = Oficina.query.filter_by(cliente_id=current_user.cliente_id).all()
            oficinas.extend(oficinas_cliente)
            logger.debug(f"DEBUG [48] -> Encontradas {len(oficinas_cliente)} oficinas pelo cliente_id")
    
    logger.debug(f"DEBUG [49] -> Total de oficinas encontradas: {len(oficinas)}")

    # Filtra oficinas pelo evento selecionado (inclui atividades gerais)
    if selected_event_id is not None:
        oficinas = [
            o for o in oficinas if o.evento_id == selected_event_id or o.evento_id is None
        ]
        logger.debug(
            "DEBUG [49A] -> Oficinas após filtro por evento %s: %s",
            selected_event_id,
            len(oficinas),
        )

    if current_user.tipo_inscricao and getattr(current_user.tipo_inscricao, 'submission_only', False):
        oficinas = []

    # CORREÇÃO 7: Filtrar inscrições válidas (com oficina_id não nulo)
    logger.debug(f"DEBUG [50] -> Montando lista de inscrições do participante_id = {current_user.id}")
    inscricoes_ids = [i.oficina_id for i in inscricoes_validas if i.oficina_id is not None]
    logger.debug(f"DEBUG [51] -> Participante inscrito em {len(inscricoes_ids)} oficinas válidas: {inscricoes_ids}")
    
    # Lógica para professores verem horários disponíveis
    logger.debug(f"DEBUG [52] -> Buscando horários disponíveis para visitação")
    horarios_disponiveis = HorarioVisitacao.query.filter(
        HorarioVisitacao.vagas_disponiveis > 0,
        HorarioVisitacao.data >= datetime.now().date()
    ).all()
    logger.debug(f"DEBUG [53] -> Encontrados {len(horarios_disponiveis)} horários disponíveis")

    # Verificar se o evento atual possui horários disponíveis e configuração de
    # agendamento habilitada
    tem_horarios_agendamento = False
    if evento:
        horarios_evento = [h for h in horarios_disponiveis if h.evento_id == evento.id]
        tem_horarios_agendamento = bool(horarios_evento) and bool(evento.configuracoes_agendamento)
    logger.debug(
        f"DEBUG [53A] -> Evento possui horários para agendamento? {tem_horarios_agendamento}"
    )

    # Carregar regras de inscrição para o tipo de inscrição do usuário por evento
    logger.debug(f"DEBUG [54] -> Carregando regras de inscrição para tipo_inscricao_id = {current_user.tipo_inscricao_id}")
    regras_inscricao = {}
    
    if current_user.tipo_inscricao_id:
        logger.debug(f"DEBUG [55] -> Verificando regras para cada evento")
        # Para cada evento disponível, verificar as regras para o tipo de inscrição do usuário
        for evento_id in todos_eventos_ids:
            logger.debug(f"DEBUG [56] -> Buscando regra para evento_id = {evento_id}, tipo_inscricao_id = {current_user.tipo_inscricao_id}")
            regra = RegraInscricaoEvento.query.filter_by(
                evento_id=evento_id,
                tipo_inscricao_id=current_user.tipo_inscricao_id
            ).first()
            
            if regra:
                oficinas_permitidas = regra.get_oficinas_permitidas_list()
                regras_inscricao[evento_id] = {
                    'limite_oficinas': regra.limite_oficinas,
                    'oficinas_permitidas': set(oficinas_permitidas)
                }
                logger.debug(f"DEBUG [57] -> Regra encontrada: limite={regra.limite_oficinas}, oficinas_permitidas={len(oficinas_permitidas)}")
            else:
                logger.debug(f"DEBUG [58] -> Nenhuma regra encontrada para este evento/tipo de inscrição")
    
    # Contar inscrições do usuário por evento
    logger.debug(f"DEBUG [59] -> Contando inscrições do usuário por evento")
    inscricoes_por_evento = {}
    for inscricao in inscricoes_validas:
        evento_id = None
        if inscricao.oficina and inscricao.oficina.evento_id:
            evento_id = inscricao.oficina.evento_id
        elif inscricao.evento_id:
            evento_id = inscricao.evento_id

        if evento_id:
            if evento_id not in inscricoes_por_evento:
                inscricoes_por_evento[evento_id] = 0
            inscricoes_por_evento[evento_id] += 1
            logger.debug(
                f"DEBUG [60] -> Evento {evento_id}: {inscricoes_por_evento[evento_id]} inscrições"
            )
    
    # Monte a estrutura que o template "dashboard_participante.html" precisa
    logger.debug(f"DEBUG [61] -> Formatando {len(oficinas)} oficinas para exibição")
    oficinas_formatadas = []
    
    # CORREÇÃO 8: Garantir que todas as oficinas estejam devidamente processadas
    for idx, oficina in enumerate(oficinas):
        logger.debug(f"DEBUG [62] -> Processando oficina {idx+1}/{len(oficinas)}: id={oficina.id}, título={oficina.titulo}")
        
        logger.debug(f"DEBUG [63] -> Buscando dias para oficina_id = {oficina.id}")
        dias = OficinaDia.query.filter_by(oficina_id=oficina.id).all()
        logger.debug(f"DEBUG [64] -> Encontrados {len(dias)} dias para esta oficina")
        
        # Verificar se a oficina está disponível para o tipo de inscrição do usuário
        disponivel_para_inscricao = True
        motivo_indisponibilidade = None
        
        # CORREÇÃO 9: Tratamento para oficinas sem evento
        evento_id = oficina.evento_id
        evento_nome = "Atividades Gerais"  # Nome padrão para oficinas sem evento
        evento_encerrado = False
        evento_futuro = False
        evento_info = None
        
        # Se a oficina tiver evento associado, pegar informações do evento
        if evento_id:
            logger.debug(f"DEBUG [65] -> Oficina tem evento_id = {evento_id}")
            if oficina.evento:
                evento_nome = oficina.evento.nome
                logger.debug(f"DEBUG [66] -> Nome do evento: {evento_nome}")
            
            # Verificar disponibilidade para tipo de inscrição
            if current_user.tipo_inscricao_id:
                logger.debug(f"DEBUG [67] -> Verificando disponibilidade para tipo_inscricao_id = {current_user.tipo_inscricao_id}, evento_id = {evento_id}")
                # Obter regras para este evento específico
                regra_evento = regras_inscricao.get(evento_id, {})
                
                # Se há oficinas permitidas definidas e esta oficina não está na lista
                oficinas_permitidas = regra_evento.get('oficinas_permitidas', set())
                if oficinas_permitidas:
                    logger.debug(f"DEBUG [68] -> Verificando se oficina {oficina.id} está entre as {len(oficinas_permitidas)} oficinas permitidas")
                    if oficina.id not in oficinas_permitidas:
                        disponivel_para_inscricao = False
                        motivo_indisponibilidade = "Seu tipo de inscrição não permite acesso a esta oficina"
                        logger.debug(f"DEBUG [69] -> Oficina indisponível: não está na lista de permitidas")
                
                # Se há limite de oficinas e o usuário já atingiu o limite
                limite_oficinas = regra_evento.get('limite_oficinas', 0)
                if limite_oficinas > 0 and evento_id in inscricoes_por_evento:
                    logger.debug(f"DEBUG [70] -> Verificando limite de inscrições: atual={inscricoes_por_evento[evento_id]}, limite={limite_oficinas}")
                    if inscricoes_por_evento[evento_id] >= limite_oficinas and oficina.id not in inscricoes_ids:
                        disponivel_para_inscricao = False
                        motivo_indisponibilidade = f"Você já atingiu o limite de {limite_oficinas} oficinas para seu tipo de inscrição"
                        logger.debug(f"DEBUG [71] -> Oficina indisponível: limite de inscrições atingido")
            
            # Obter informações do evento desta oficina
            logger.debug(f"DEBUG [72] -> Buscando informações do evento para oficina_id = {oficina.id}, evento_id = {evento_id}")
            if evento_id in eventos_info:
                evento_info = eventos_info[evento_id]
                evento_encerrado = evento_info['ja_ocorreu']
                evento_futuro = evento_info['eh_futuro']
                logger.debug(f"DEBUG [73] -> Evento encontrado: encerrado={evento_encerrado}, futuro={evento_futuro}, status={evento_info['status']}")
            else:
                # CORREÇÃO 10: Se o evento não estiver em eventos_info, criar uma entrada padrão
                logger.debug(f"DEBUG [74] -> Evento não encontrado nas informações processadas, adicionando informação padrão")
                if oficina.evento:
                    # Calcular status baseado nas datas do evento
                    ja_ocorreu = False
                    eh_futuro = False
                    if oficina.evento.data_fim:
                        data_fim = oficina.evento.data_fim
                        if hasattr(data_fim, 'date'):
                            data_fim = data_fim.date()
                        ja_ocorreu = data_fim < data_atual
                    
                    if oficina.evento.data_inicio:
                        data_inicio = oficina.evento.data_inicio
                        if hasattr(data_inicio, 'date'):
                            data_inicio = data_inicio.date()
                        eh_futuro = data_inicio > data_atual
                    
                    status = 'Futuro' if eh_futuro else ('Encerrado' if ja_ocorreu else 'Atual')
                    
                    eventos_info[evento_id] = {
                        'id': evento_id,
                        'nome': evento_nome,
                        'data_inicio': oficina.evento.data_inicio,
                        'data_fim': oficina.evento.data_fim,
                        'ja_ocorreu': ja_ocorreu,
                        'eh_futuro': eh_futuro,
                        'status': status
                    }
                    
                    evento_encerrado = ja_ocorreu
                    evento_futuro = eh_futuro
                    evento_info = eventos_info[evento_id]
                    logger.debug(f"DEBUG [75] -> Adicionando evento {evento_id} como {status}")
        else:
            # CORREÇÃO 11: Para oficinas sem evento, considerar como eventos atuais
            logger.debug(f"DEBUG [76] -> Oficina sem evento_id, tratando como 'Atividades Gerais'")
            evento_id = 'sem_evento'  # Um marcador para identificar
            evento_encerrado = False
            evento_futuro = False
        
        logger.debug(f"DEBUG [77] -> Adicionando oficina formatada: id={oficina.id}, disponível={disponivel_para_inscricao}")
        oficinas_formatadas.append({
            'id': oficina.id,
            'titulo': oficina.titulo,
            'descricao': oficina.descricao,
            'ministrantes': [m.nome for m in oficina.ministrantes_associados] if hasattr(oficina, 'ministrantes_associados') and oficina.ministrantes_associados else [],
            'vagas': oficina.vagas,
            'carga_horaria': oficina.carga_horaria,
            'dias': dias,
            'evento_id': evento_id,
            'evento_nome': evento_nome,
            'tipo_inscricao': oficina.tipo_inscricao,
            'disponivel_para_inscricao': disponivel_para_inscricao,
            'motivo_indisponibilidade': motivo_indisponibilidade,
            'evento_encerrado': evento_encerrado,
            'evento_futuro': evento_futuro,
            'evento_data_inicio': evento_info['data_inicio'] if evento_info else None,
            'evento_data_fim': evento_info['data_fim'] if evento_info else None,
            'evento_status': evento_info['status'] if evento_info else 'Atual'
        })

    logger.debug(f"DEBUG [78] -> Estatísticas finais de oficinas:")
    logger.debug(f"DEBUG [79] -> Total de oficinas formatadas: {len(oficinas_formatadas)}")
    logger.debug(f"DEBUG [80] -> Oficinas de eventos abertos: {len([o for o in oficinas_formatadas if not o['evento_encerrado']])}")
    logger.debug(f"DEBUG [81] -> Oficinas de eventos futuros: {len([o for o in oficinas_formatadas if o['evento_futuro']])}")
    logger.debug(f"DEBUG [82] -> Oficinas de eventos encerrados: {len([o for o in oficinas_formatadas if o['evento_encerrado']])}")
    logger.debug(f"DEBUG [83] -> Oficinas sem evento: {len([o for o in oficinas_formatadas if o['evento_id'] == 'sem_evento'])}")
    logger.debug(f"DEBUG [84] -> Oficinas disponíveis para inscrição: {len([o for o in oficinas_formatadas if o['disponivel_para_inscricao']])}")

    # CORREÇÃO 12: Garantir que mostraremos todas as oficinas, mesmo se todos os eventos estiverem encerrados
    logger.debug(f"DEBUG [85] -> Renderizando template dashboard_participante.html")
    
     # NOVA CORREÇÃO: agrupar eventos por status usando eventos_info
    eventos_futuros = [e for e in eventos_sorted if eventos_info.get(e.id, {}).get('eh_futuro')]
    eventos_atuais = [e for e in eventos_sorted if not eventos_info.get(e.id, {}).get('eh_futuro')
                       and not eventos_info.get(e.id, {}).get('ja_ocorreu')]
    eventos_encerrados = [e for e in eventos_sorted if eventos_info.get(e.id, {}).get('ja_ocorreu')]
    logger.debug(f"DEBUG -> Eventos futuros: {len(eventos_futuros)}, atuais: {len(eventos_atuais)}, encerrados: {len(eventos_encerrados)}")
    
    return render_template(
        'dashboard_participante.html',
        config_cliente=config_cliente,
        usuario=current_user,
        evento=evento,
        eventos=eventos,
        eventos_sorted=eventos_sorted,
        eventos_futuros=eventos_futuros,
        eventos_atuais=eventos_atuais,
        eventos_encerrados=eventos_encerrados,
        oficinas=oficinas_formatadas,
        eventos_inscritos=eventos_inscritos,
        todos_eventos_ids=todos_eventos_ids,
        eventos_info=eventos_info,
        data_atual=data_atual,
        permitir_checkin_global=permitir_checkin,
        habilitar_feedback=habilitar_feedback,
        habilitar_certificado_individual=habilitar_certificado,
        formularios_disponiveis=formularios_disponiveis,
        horarios_disponiveis=horarios_disponiveis,
        tem_horarios_agendamento=tem_horarios_agendamento,
        # Variáveis para diagnóstico
        debug_total_oficinas=len(oficinas_formatadas),
        debug_oficinas_encerradas=len([o for o in oficinas_formatadas if o['evento_encerrado']]),
        debug_oficinas_futuras=len([o for o in oficinas_formatadas if o['evento_futuro']]),
        debug_oficinas_atuais=len([o for o in oficinas_formatadas if not o['evento_encerrado'] and not o['evento_futuro']]),
        debug_oficinas_sem_evento=len([o for o in oficinas_formatadas if o['evento_id'] == 'sem_evento']),
        # CORREÇÃO: Forçar exibição de todos os tipos de eventos
        forcar_exibir_encerrados=True
    )

# ---------------------------------------------------------------------------
# Utilidades locais
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    """Retorna agora em UTC"""
    return datetime.now(timezone.utc)


def _primeiro_valido(*values):
    """Retorna o primeiro valor truthy (helper simples)."""
    return next((v for v in values if v), None)


def _checar_duplicado(email: str, cpf: str) -> Optional[str]:
    duplicado = Usuario.query.filter(
        (Usuario.email == email) | (Usuario.cpf == cpf)
    ).first()
    if not duplicado:
        return None
    return "E‑mail já cadastrado." if duplicado.email == email else "CPF já cadastrado."


class LoteEsgotadoError(RuntimeError):
    pass
