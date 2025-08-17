from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, cast, Date, func, text
from werkzeug.utils import secure_filename
from datetime import datetime, date, time
from collections import defaultdict
import os


from extensions import db
import logging

logger = logging.getLogger(__name__)
from models import (
    Evento, Oficina, LinkCadastro, LoteInscricao, EventoInscricaoTipo,
    Usuario, RegraInscricaoEvento, LoteTipoInscricao, Inscricao,
    ConfiguracaoCertificadoEvento, Checkin, OficinaDia, MaterialOficina,
    RelatorioOficina, ConfiguracaoAgendamento, SalaVisitacao,
    HorarioVisitacao, AgendamentoVisita, AlunoVisitante,
    ProfessorBloqueado, Patrocinador, Sorteio, Submission,
    Feedback, Pagamento, ConfiguracaoCliente, ConfiguracaoEvento
)
from utils import preco_com_taxa

evento_routes = Blueprint('evento_routes', __name__, template_folder="../templates")


@evento_routes.route('/')
def home():
    """Renderiza index.html mostrando eventos cujo período AINDA não acabou."""
    try:
        hoje = date.today()
        eventos = (Evento.query
                   .filter(
                       Evento.status == 'ativo',
                       Evento.publico.is_(True),
                       # ⬇️ critério novo
                       or_(Evento.data_fim == None,
                           cast(Evento.data_fim, Date) >= hoje)
                   )
                   .order_by(Evento.data_inicio.asc())
                   .all())

        return render_template('index.html',
                               eventos_destaque=_serializa_eventos(eventos))
    except Exception as e:
        logger.error("home(): %s", e)
        db.session.rollback()  # ensure session not left in failed state
        return render_template('index.html', eventos_destaque=[])

@evento_routes.route('/evento/<int:evento_id>/inscricao')
def inscricao_evento(evento_id):
    """
    Redireciona para a página de inscrição do evento usando o LinkCadastro existente
    ou para a inscrição direta caso o evento permita
    """
    evento = Evento.query.get_or_404(evento_id)
    
    # 1. Primeiro verifica se o evento está ativo
    if evento.status != 'ativo':
        flash('Este evento não está disponível para inscrições no momento.', 'warning')
        return redirect(url_for('evento_routes.visualizar_evento', evento_id=evento_id))
    
    # 2. Busca o link de cadastro mais recente para este evento
    link = (
        LinkCadastro.query
        .filter_by(evento_id=evento_id)
        .order_by(LinkCadastro.criado_em.desc())
        .first()
    )
    
    if link:
        # Se existe um link personalizado, usa ele
        if link.slug_customizado:
            return redirect(url_for('inscricao_routes.cadastro_participante', identifier=link.slug_customizado))
        # Senão, usa o token
        return redirect(url_for('inscricao_routes.cadastro_participante', identifier=link.token))
    
    # 3. Se não existe link, verifica se o evento permite inscrição direta
    if evento.publico and not evento.requer_aprovacao:
        # Aqui está a correção - não usamos mais link.token pois link é None
        # Criamos um token temporário ou usamos um método alternativo
        return redirect(url_for('inscricao_routes.cadastro_participante', identifier=evento_id))
    
    # 4. Fallback final
    flash('Este evento não possui inscrições abertas no momento.', 'warning')
    return redirect(url_for('evento_routes.visualizar_evento', evento_id=evento_id))

@evento_routes.route('/api/eventos/destaque')
def api_eventos_destaque():
    hoje = date.today()
    eventos = (Evento.query
               .filter(
                   Evento.status == 'ativo',
                   Evento.publico.is_(True),
                   or_(Evento.data_fim == None,
                       func.date(Evento.data_fim) >= hoje)
               )
               .order_by(Evento.data_inicio))
    return jsonify(_serializa_eventos(eventos))

    
# ------------------------------------------------------------------
# Função auxiliar DRY
def _serializa_eventos(eventos):
    lista = []
    for ev in eventos:
        preco_base = min((t.preco for t in ev.tipos_inscricao), default=0)
        dado = {
            'id':          ev.id,
            'nome':        ev.nome,
            'descricao':   ev.descricao,
            'data_inicio': ev.data_inicio.strftime('%d/%m/%Y')
                           if ev.data_inicio else 'Data a definir',
            'data_fim':    ev.data_fim.strftime('%d/%m/%Y')
                           if ev.data_fim else '',
            'localizacao': ev.localizacao or 'Local a definir',
            'banner_url':  ev.banner_url or url_for('static',
                                                    filename='images/event-placeholder.jpg'),
            'preco_base':  preco_base,
            'preco_final': float(preco_com_taxa(preco_base)),
            'link_inscricao': None
        }

        # link de inscrição (se houver)
        if ev.links_cadastro:
            link = ev.links_cadastro[0]
            dado['link_inscricao'] = (
                url_for('inscricao_routes.cadastro_participante', identifier=link.slug_customizado)
                if link.slug_customizado else
                url_for('inscricao_routes.cadastro_participante', identifier=link.token)
            )
        else:
            # Habilita inscrição se o evento estiver em andamento (data atual entre início e fim)
            hoje = date.today()
            data_inicio = ev.data_inicio.date() if ev.data_inicio else None
            data_fim = ev.data_fim.date() if ev.data_fim else None

            if data_inicio and (data_inicio <= hoje <= (data_fim or data_inicio)):
                dado['link_inscricao'] = url_for('evento_routes.inscricao_evento', evento_id=ev.id)

        lista.append(dado)
    return lista

@evento_routes.route('/eventos')
def listar_eventos():
    try:
        # Lista completa de eventos
        eventos = Evento.query.filter(
            Evento.data_inicio >= datetime.now(),
            Evento.status == 'ativo',
            Evento.publico == True  # adicionado filtro de eventos públicos
        ).order_by(Evento.data_inicio.asc()).all()
        
        # Processa os eventos para o template
        eventos_processed = []
        for evento in eventos:
            evento_dict = {
                'id': evento.id,
                'nome': evento.nome,
                # adicione outros campos necessários para o template eventos_disponiveis.html
                'data_inicio': evento.data_inicio.strftime('%d/%m/%Y') if evento.data_inicio else 'Data a definir',
                'localizacao': evento.localizacao or 'Local a definir',
                'preco_base': 0
            }
            
            if evento.tipos_inscricao and len(evento.tipos_inscricao) > 0:
                evento_dict['preco_base'] = min(tipo.preco for tipo in evento.tipos_inscricao)
            
            eventos_processed.append(evento_dict)
        
        return render_template('evento/eventos_disponiveis.html', eventos=eventos_processed)
    
    except Exception as e:
        logger.error("Erro em listar_eventos: %s", str(e))
        return render_template('evento/eventos_disponiveis.html', eventos=[])

@evento_routes.route('/configurar_evento', methods=['GET', 'POST'])
@login_required
def configurar_evento():
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))

    # Lista apenas eventos ativos do cliente
    eventos = Evento.query.filter_by(cliente_id=current_user.id, status='ativo').all()
    
    # Evento selecionado (por padrão, None até que o usuário escolha)
    evento_id = request.args.get('evento_id') or (request.form.get('evento_id') if request.method == 'POST' else None)
    evento = None
    config_certificado = None
    oficinas = []
    if evento_id:
        # Carregamento eager de todos os relacionamentos necessários
        evento = (
            Evento.query.options(
                db.joinedload(Evento.tipos_inscricao),
                db.joinedload(Evento.lotes).joinedload(LoteInscricao.tipos_inscricao)
            )
            .filter_by(id=evento_id, cliente_id=current_user.id, status='ativo')
            .first()
        )
        if evento:
            config_certificado = ConfiguracaoCertificadoEvento.query.filter_by(evento_id=evento.id).first()
            oficinas = Oficina.query.filter_by(evento_id=evento.id).order_by(Oficina.titulo).all()

    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        programacao = request.form.get('programacao')
        localizacao = request.form.get('localizacao')
        link_mapa = request.form.get('link_mapa')
        inscricao_gratuita_val = request.form.get('inscricao_gratuita')
        inscricao_gratuita = inscricao_gratuita_val in ['on', '1', 'true']
        habilitar_lotes_val = request.form.get('habilitar_lotes')
        habilitar_lotes = habilitar_lotes_val in ['on', '1', 'true']
        nomes_tipos = request.form.getlist('nome_tipo[]')  # Lista de nomes dos tipos
        precos_tipos = request.form.getlist('preco_tipo[]')  # Lista de preços dos tipos
        submission_flags = request.form.getlist('submission_only[]')

        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')
        hora_inicio_str = request.form.get('hora_inicio')
        hora_fim_str = request.form.get('hora_fim')

        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d') if data_inicio_str else None
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d') if data_fim_str else None
        hora_inicio = time.fromisoformat(hora_inicio_str) if hora_inicio_str else None
        hora_fim = time.fromisoformat(hora_fim_str) if hora_fim_str else None
        
        banner = request.files.get('banner')
        banner_url = evento.banner_url if evento else None
        
        if banner:
            filename = secure_filename(banner.filename)
            caminho_banner = os.path.join('static/banners', filename)
            os.makedirs(os.path.dirname(caminho_banner), exist_ok=True)
            banner.save(caminho_banner)
            banner_url = url_for('static', filename=f'banners/{filename}', _external=True)

        try:
            if evento:  # Atualizar evento existente
                evento.nome = nome
                evento.descricao = descricao
                evento.programacao = programacao
                evento.localizacao = localizacao
                evento.link_mapa = link_mapa
                evento.inscricao_gratuita = inscricao_gratuita
                evento.habilitar_lotes = habilitar_lotes  # Novo campo
                evento.data_inicio = data_inicio
                evento.data_fim = data_fim
                evento.hora_inicio = hora_inicio
                evento.hora_fim = hora_fim
                if banner_url:
                    evento.banner_url = banner_url

                # Remover regras de inscrição associadas para evitar violação de chave estrangeira
                RegraInscricaoEvento.query.filter_by(evento_id=evento.id).delete()
                
                # Verifica se existem usuários vinculados aos tipos de inscrição deste evento
                tipos_com_usuarios = db.session.query(EventoInscricaoTipo.id).join(
                    Usuario, Usuario.tipo_inscricao_id == EventoInscricaoTipo.id
                ).filter(
                    EventoInscricaoTipo.evento_id == evento.id
                ).all()
                
                # Lista de IDs de tipos que têm usuários vinculados
                ids_tipos_com_usuarios = [tipo[0] for tipo in tipos_com_usuarios]
                
                # Verifica quais tipos têm referências na tabela lote_tipo_inscricao
                tipos_com_lotes = db.session.query(LoteTipoInscricao.tipo_inscricao_id).join(
                    EventoInscricaoTipo, LoteTipoInscricao.tipo_inscricao_id == EventoInscricaoTipo.id
                ).filter(
                    EventoInscricaoTipo.evento_id == evento.id
                ).distinct().all()
                
                # Lista de IDs de tipos que têm lotes vinculados
                ids_tipos_com_lotes = [tipo[0] for tipo in tipos_com_lotes]
                
                # Primeiro, remover as referências de lote_tipo_inscricao para os tipos que serão removidos
                ids_tipos_para_preservar = list(set(ids_tipos_com_usuarios))
                
                # Lista de IDs que foram enviados pelo formulário
                ids_tipos_enviados = []
                for i, nome_tipo in enumerate(nomes_tipos):
                    if nome_tipo and i < len(request.form.getlist('id_tipo[]')):
                        tipo_id = request.form.getlist('id_tipo[]')[i]
                        if tipo_id and tipo_id.isdigit():
                            ids_tipos_enviados.append(int(tipo_id))
                
                # Adicionar os tipos enviados pelo formulário à lista de preservação
                ids_tipos_para_preservar.extend([tid for tid in ids_tipos_enviados if tid not in ids_tipos_para_preservar])
                
                # Remover referências em lote_tipo_inscricao para tipos que serão excluídos
                for tipo_id in ids_tipos_com_lotes:
                    if tipo_id not in ids_tipos_para_preservar:
                        LoteTipoInscricao.query.filter_by(tipo_inscricao_id=tipo_id).delete()
                
                # Agora podemos excluir os tipos de inscrição com segurança
                if ids_tipos_para_preservar:
                    # Exclui apenas os tipos que NÃO estão na lista de preservação
                    EventoInscricaoTipo.query.filter(
                        EventoInscricaoTipo.evento_id == evento.id,
                        ~EventoInscricaoTipo.id.in_(ids_tipos_para_preservar)
                    ).delete(synchronize_session=False)
                else:
                    # Se não houver tipos para preservar, primeiro remova todas as referências
                    LoteTipoInscricao.query.filter(
                        LoteTipoInscricao.tipo_inscricao_id.in_(
                            db.session.query(EventoInscricaoTipo.id).filter_by(evento_id=evento.id)
                        )
                    ).delete(synchronize_session=False)
                    # Depois exclua todos os tipos
                    EventoInscricaoTipo.query.filter_by(evento_id=evento.id).delete()
                
                # Adicionar novos tipos ou atualizar existentes
                tipos_inscricao = []
                for idx, (nome_tipo, preco_tipo) in enumerate(zip(nomes_tipos, precos_tipos)):
                    if nome_tipo:  # Só adicionar se o nome for preenchido
                        # Se o preço estiver vazio, trata como 0
                        preco_tipo_str = preco_tipo.strip() if preco_tipo else ''
                        preco_efetivo = 0.0 if inscricao_gratuita or preco_tipo_str == '' else float(preco_tipo_str)
                        flag = idx < len(submission_flags) and submission_flags[idx] in ['on', '1', 'true']
                        
                        # Verificar se já existe um tipo com este nome
                        tipo_existente = None
                        for tipo_id in ids_tipos_para_preservar:
                            tipo = EventoInscricaoTipo.query.get(tipo_id)
                            if tipo and tipo.nome == nome_tipo:
                                tipo_existente = tipo
                                break
                        
                        if tipo_existente:
                            # Atualiza o preço do tipo existente
                            tipo_existente.preco = preco_efetivo
                            tipo_existente.submission_only = flag
                            tipos_inscricao.append(tipo_existente)
                        else:
                            # Cria um novo tipo
                            tipo = EventoInscricaoTipo(
                                evento_id=evento.id,
                                nome=nome_tipo,
                                preco=preco_efetivo,
                                submission_only=flag
                            )
                            db.session.add(tipo)
                            db.session.flush()  # Para obter o ID do tipo
                            tipos_inscricao.append(tipo)
                
                # Processar os lotes somente se habilitar_lotes for True
                if habilitar_lotes:
                    lote_ids = request.form.getlist('lote_id[]')
                    lote_nomes = request.form.getlist('lote_nome[]')
                    lote_ordens = request.form.getlist('lote_ordem[]')
                    lote_ativo = [val == '1' for val in request.form.getlist('lote_ativo[]')]
                    lote_usar_data = [val == 'on' for val in request.form.getlist('lote_usar_data[]')]
                    lote_data_inicio = request.form.getlist('lote_data_inicio[]')
                    lote_data_fim = request.form.getlist('lote_data_fim[]')
                    lote_usar_qtd = [val == 'on' for val in request.form.getlist('lote_usar_qtd[]')]
                    lote_qtd_maxima = request.form.getlist('lote_qtd_maxima[]')
                    
                    # Verificar quais lotes possuem inscrições
                    lotes_com_inscricoes = db.session.query(LoteInscricao.id).join(
                        Inscricao, Inscricao.lote_id == LoteInscricao.id
                    ).filter(
                        LoteInscricao.evento_id == evento.id
                    ).all()
                    
                    # Lista de IDs de lotes com inscrições vinculadas
                    ids_lotes_com_inscricoes = [lote_id[0] for lote_id in lotes_com_inscricoes]
                    
                    # IDs de lotes que devem ser preservados (informados pelo cliente via form)
                    preservar_ids_lote = request.form.get('preservar_ids_lote', '').split(',')
                    preservar_ids_lote = [int(id) for id in preservar_ids_lote if id and id.isdigit()]
                    
                    # Lotes a serem removidos
                    lotes_para_remover = LoteInscricao.query.filter(
                        LoteInscricao.evento_id == evento.id,
                        ~LoteInscricao.id.in_(preservar_ids_lote),
                        ~LoteInscricao.id.in_(ids_lotes_com_inscricoes)
                    ).all()
                    
                    # Remover os registros de lote_tipo_inscricao antes de remover os lotes
                    for lote in lotes_para_remover:
                        LoteTipoInscricao.query.filter_by(lote_id=lote.id).delete()
                    
                    # Agora é seguro remover os lotes
                    for lote in lotes_para_remover:
                        db.session.delete(lote)
                    
                    # Processar cada lote
                    for i, nome in enumerate(lote_nomes):
                        if nome:
                            # Determinar configurações do lote
                            data_inicio_lote = None
                            data_fim_lote = None
                            qtd_maxima = None
                            ativo = True if i < len(lote_ativo) and lote_ativo[i] else False
                            
                            if i < len(lote_usar_data) and lote_usar_data[i]:
                                if i < len(lote_data_inicio) and lote_data_inicio[i]:
                                    data_inicio_lote = datetime.strptime(lote_data_inicio[i], '%Y-%m-%d')
                                if i < len(lote_data_fim) and lote_data_fim[i]:
                                    data_fim_lote = datetime.strptime(lote_data_fim[i], '%Y-%m-%d')
                            
                            if i < len(lote_usar_qtd) and lote_usar_qtd[i]:
                                if i < len(lote_qtd_maxima) and lote_qtd_maxima[i]:
                                    qtd_maxima = int(lote_qtd_maxima[i])
                            
                            # Verificar se é um lote existente ou novo
                            lote_id = lote_ids[i] if i < len(lote_ids) and lote_ids[i] else None
                            
                            if lote_id:
                                # Atualizar lote existente
                                lote = LoteInscricao.query.get(int(lote_id))
                                if lote:
                                    lote.nome = nome
                                    lote.data_inicio = data_inicio_lote
                                    lote.data_fim = data_fim_lote
                                    lote.qtd_maxima = qtd_maxima
                                    lote.ordem = int(lote_ordens[i]) if i < len(lote_ordens) else i+1
                                    lote.ativo = ativo
                            else:
                                # Criar novo lote
                                lote = LoteInscricao(
                                    evento_id=evento.id,
                                    nome=nome,
                                    data_inicio=data_inicio_lote,
                                    data_fim=data_fim_lote,
                                    qtd_maxima=qtd_maxima,
                                    ordem=int(lote_ordens[i]) if i < len(lote_ordens) else i+1,
                                    ativo=ativo
                                )
                                db.session.add(lote)
                                db.session.flush()  # Para obter o ID
                            
                            # Processar preços dos tipos de inscrição para este lote
                            for tipo in tipos_inscricao:
                                # O formato do nome do campo: lote_tipo_preco_[lote_id]_[tipo_id]
                                preco_key = f'lote_tipo_preco_{lote.id}_{tipo.id}'
                                preco_valor = request.form.get(preco_key)

                                if preco_valor is not None:
                                    preco_valor = preco_valor.strip()
                                    # Se o valor estiver vazio ou for gratuito, usar 0
                                    preco_final = 0.0 if inscricao_gratuita or preco_valor == '' else float(preco_valor)
                                    
                                    # Verificar se já existe um registro de preço para este lote e tipo
                                    lote_tipo = LoteTipoInscricao.query.filter_by(
                                        lote_id=lote.id, 
                                        tipo_inscricao_id=tipo.id
                                    ).first()
                                    
                                    if lote_tipo:
                                        # Atualizar preço existente
                                        lote_tipo.preco = preco_final
                                    else:
                                        # Criar novo registro de preço
                                        novo_lote_tipo = LoteTipoInscricao(
                                            lote_id=lote.id,
                                            tipo_inscricao_id=tipo.id,
                                            preco=preco_final
                                        )
                                        db.session.add(novo_lote_tipo)
                
            else:  # Criar novo evento
                evento = Evento(
                    cliente_id=current_user.id,
                    nome=nome,
                    descricao=descricao,
                    programacao=programacao,
                    localizacao=localizacao,
                    link_mapa=link_mapa,
                    banner_url=banner_url,
                    inscricao_gratuita=inscricao_gratuita,
                    habilitar_lotes=habilitar_lotes,  # Novo campo
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    hora_inicio=hora_inicio,
                    hora_fim=hora_fim,
                )
                db.session.add(evento)
                db.session.flush()  # Gera o ID do evento antes de adicionar os tipos

                # Adicionar tipos de inscrição
                tipos_inscricao = []
                for idx, (nome_tipo, preco_tipo) in enumerate(zip(nomes_tipos, precos_tipos)):
                    if nome_tipo:  # Só adicionar se o nome for preenchido
                        # Se o preço estiver vazio, trata como 0
                        preco_tipo_str = preco_tipo.strip() if preco_tipo else ''
                        preco_efetivo = 0.0 if inscricao_gratuita or preco_tipo_str == '' else float(preco_tipo_str)
                        flag = idx < len(submission_flags) and submission_flags[idx] in ['on', '1', 'true']

                        tipo = EventoInscricaoTipo(
                            evento_id=evento.id,
                            nome=nome_tipo,
                            preco=preco_efetivo,
                            submission_only=flag
                        )
                        db.session.add(tipo)
                        db.session.flush()  # Para obter o ID
                        tipos_inscricao.append(tipo)
                
                # Adicionar lotes de inscrição somente se habilitar_lotes for True
                if habilitar_lotes:
                    lote_nomes = request.form.getlist('lote_nome[]')
                    lote_ordens = request.form.getlist('lote_ordem[]')
                    lote_ativo = [val == '1' for val in request.form.getlist('lote_ativo[]')]
                    lote_usar_data = [val == 'on' for val in request.form.getlist('lote_usar_data[]')]
                    lote_data_inicio = request.form.getlist('lote_data_inicio[]')
                    lote_data_fim = request.form.getlist('lote_data_fim[]')
                    lote_usar_qtd = [val == 'on' for val in request.form.getlist('lote_usar_qtd[]')]
                    lote_qtd_maxima = request.form.getlist('lote_qtd_maxima[]')
                    
                    # Criar cada lote
                    for i, nome in enumerate(lote_nomes):
                        if nome:
                            # Determinar configurações do lote
                            data_inicio_lote = None
                            data_fim_lote = None
                            qtd_maxima = None
                            ativo = True if i < len(lote_ativo) and lote_ativo[i] else False
                            
                            if i < len(lote_usar_data) and lote_usar_data[i]:
                                if i < len(lote_data_inicio) and lote_data_inicio[i]:
                                    data_inicio_lote = datetime.strptime(lote_data_inicio[i], '%Y-%m-%d')
                                if i < len(lote_data_fim) and lote_data_fim[i]:
                                    data_fim_lote = datetime.strptime(lote_data_fim[i], '%Y-%m-%d')
                            
                            if i < len(lote_usar_qtd) and lote_usar_qtd[i]:
                                if i < len(lote_qtd_maxima) and lote_qtd_maxima[i]:
                                    qtd_maxima = int(lote_qtd_maxima[i])
                            
                            # Criar o lote
                            lote = LoteInscricao(
                                evento_id=evento.id,
                                nome=nome,
                                data_inicio=data_inicio_lote,
                                data_fim=data_fim_lote,
                                qtd_maxima=qtd_maxima,
                                ordem=int(lote_ordens[i]) if i < len(lote_ordens) else i+1,
                                ativo=ativo
                            )
                            db.session.add(lote)
                            db.session.flush()  # Para obter o ID do lote
                            
                            # Processar preços por tipo de inscrição
                            for j, tipo in enumerate(tipos_inscricao):
                                # Para novos lotes e tipos, o formato pode variar
                                preco_key = f'lote_tipo_preco_new_{i}_{tipo.id}' if tipo.id else f'lote_tipo_preco_new_{i}_new_{j}'
                                # Verificar também o formato alternativo para compatibilidade

                                preco_valor = request.form.get(preco_key) or request.form.get(f'lote_tipo_preco_new_{i}_new_{j}')


                                if tipo.id:
                                    preco_valor = request.form.get(preco_key) or request.form.get(f'lote_tipo_preco_new_{i}_new_{j}')
                                else:
                                    preco_valor = request.form.get(preco_key)
                                

                                if preco_valor is not None:
                                    preco_valor = preco_valor.strip()
                                    # Se o valor estiver vazio ou for gratuito, usar 0
                                    preco_final = 0.0 if inscricao_gratuita or preco_valor == '' else float(preco_valor)
                                    
                                    novo_lote_tipo = LoteTipoInscricao(
                                        lote_id=lote.id,
                                        tipo_inscricao_id=tipo.id,
                                        preco=preco_final
                                    )
                                    db.session.add(novo_lote_tipo)

            db.session.commit()

            # Recarregar o evento com todos os relacionamentos para exibição
            if evento:
                evento = (
                    Evento.query.options(
                        db.joinedload(Evento.tipos_inscricao),
                        db.joinedload(Evento.lotes).joinedload(LoteInscricao.tipos_inscricao)
                    )
                    .filter_by(id=evento.id, cliente_id=current_user.id, status='ativo')
                    .first()
                )
                
            flash('Evento salvo com sucesso!', 'success')
            return redirect(url_for('dashboard_routes.dashboard_cliente'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar evento: {str(e)}', 'danger')
            # Adicionar log para debugging
            logger.error("Erro ao salvar evento: %s", str(e))
            import traceback
            traceback.print_exc()

    return render_template(
        "evento/configurar_evento.html",
        eventos=eventos,
        evento=evento,
        habilita_pagamento=True,
        config_certificado=config_certificado,
        oficinas=oficinas,
    )


@evento_routes.route('/salvar_config_certificado/<int:evento_id>', methods=['POST'])
@login_required
def salvar_config_certificado(evento_id):
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))

    config = ConfiguracaoCertificadoEvento.query.filter_by(evento_id=evento_id).first()
    if not config:
        config = ConfiguracaoCertificadoEvento(evento_id=evento_id, cliente_id=current_user.id)
        db.session.add(config)

    config.checkins_minimos = request.form.get('checkins_minimos', type=int) or 0
    config.percentual_minimo = request.form.get('percentual_minimo', type=int) or 0
    oficinas = request.form.getlist('oficinas_obrigatorias')
    config.oficinas_obrigatorias = ','.join(oficinas)
    db.session.commit()

    flash('Configuração de certificado atualizada!', 'success')
    return redirect(url_for('evento_routes.configurar_evento', evento_id=evento_id))


@evento_routes.route('/excluir_evento/<int:evento_id>', methods=['POST'])
@login_required
def excluir_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)

    if current_user.tipo == 'cliente' and evento.cliente_id != current_user.id:
        flash('Você não tem permissão para excluir este evento.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))

    try:
        # Desassociar usuários do evento
        Usuario.query.filter_by(evento_id=evento.id).update({'evento_id': None})

        # Excluir oficinas e dados relacionados
        for oficina in list(evento.oficinas):
            Checkin.query.filter_by(oficina_id=oficina.id).delete()
            Inscricao.query.filter_by(oficina_id=oficina.id).delete()
            OficinaDia.query.filter_by(oficina_id=oficina.id).delete()
            MaterialOficina.query.filter_by(oficina_id=oficina.id).delete()
            RelatorioOficina.query.filter_by(oficina_id=oficina.id).delete()
            Feedback.query.filter_by(oficina_id=oficina.id).delete()
            from sqlalchemy import text
            db.session.execute(
                text('DELETE FROM oficina_ministrantes_association WHERE oficina_id = :oid'),
                {'oid': oficina.id}
            )
            db.session.delete(oficina)

        # Remover check-ins diretamente do evento
        Checkin.query.filter_by(evento_id=evento.id).delete()

        # Excluir inscrições do evento
        Inscricao.query.filter_by(evento_id=evento.id).delete()

        # Excluir links de cadastro
        LinkCadastro.query.filter_by(evento_id=evento.id).delete()

        # Excluir lotes e preços
        lotes_ids = [l.id for l in evento.lotes]
        if lotes_ids:
            LoteTipoInscricao.query.filter(LoteTipoInscricao.lote_id.in_(lotes_ids)).delete(synchronize_session=False)
        LoteInscricao.query.filter_by(evento_id=evento.id).delete()

        # Remover pagamentos do evento
        Pagamento.query.filter_by(evento_id=evento.id).delete(synchronize_session=False)

        # Excluir tipos e regras de inscrição
        RegraInscricaoEvento.query.filter_by(evento_id=evento.id).delete()
        EventoInscricaoTipo.query.filter_by(evento_id=evento.id).delete()

        # Configurações e demais dependências
        ConfiguracaoAgendamento.query.filter_by(evento_id=evento.id).delete()
        ConfiguracaoCertificadoEvento.query.filter_by(evento_id=evento.id).delete()
        SalaVisitacao.query.filter_by(evento_id=evento.id).delete()
        HorarioVisitacao.query.filter_by(evento_id=evento.id).delete()
        AgendamentoVisita.query.filter(
            AgendamentoVisita.horario_id.in_(db.session.query(HorarioVisitacao.id).filter_by(evento_id=evento.id))
        ).delete(synchronize_session=False)
        AlunoVisitante.query.filter(
            AlunoVisitante.agendamento_id.in_(db.session.query(AgendamentoVisita.id).join(HorarioVisitacao).filter(HorarioVisitacao.evento_id == evento.id))
        ).delete(synchronize_session=False)
        ProfessorBloqueado.query.filter_by(evento_id=evento.id).delete()
        Patrocinador.query.filter_by(evento_id=evento.id).delete()
        Sorteio.query.filter_by(evento_id=evento.id).delete()
        Submission.query.filter_by(evento_id=evento.id).delete()

        ConfiguracaoEvento.query.filter_by(evento_id=evento.id).delete()

        db.session.delete(evento)
        db.session.commit()
        flash('Evento excluído com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir evento: {str(e)}', 'danger')

    return redirect(url_for('dashboard_routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'dashboard_routes.dashboard'))

@evento_routes.route('/exibir_evento/<int:evento_id>')
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

    # Preenche grouped_oficinas com as oficinas agrupadas por data
    for oficina in oficinas:
        for dia in oficina.dias:
            data_str = dia.data.strftime('%d/%m/%Y')
            grouped_oficinas[data_str].append({
                'titulo': oficina.titulo,
                'descricao': oficina.descricao,
                'ministrante': oficina.ministrante_obj,  # Objeto ministrante completo em vez de só o nome
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
        'evento/exibir_evento.html',
        evento=evento,
        sorted_keys=sorted_keys,
        grouped_oficinas=grouped_oficinas
    )


@evento_routes.route('/preview_evento/<int:evento_id>')
def preview_evento(evento_id):
    """Versão pública da visualização de um evento."""
    evento = Evento.query.get_or_404(evento_id)

    oficinas = Oficina.query.filter_by(cliente_id=evento.cliente_id).all()

    grouped_oficinas = defaultdict(list)
    for oficina in oficinas:
        for dia in oficina.dias:
            data_str = dia.data.strftime('%d/%m/%Y')
            grouped_oficinas[data_str].append({
                'titulo': oficina.titulo,
                'descricao': oficina.descricao,
                'ministrante': oficina.ministrante_obj,
                'horario_inicio': dia.horario_inicio,
                'horario_fim': dia.horario_fim
            })

    sorted_keys = sorted(
        grouped_oficinas.keys(),
        key=lambda d: datetime.strptime(d, '%d/%m/%Y')
    )

    return render_template(
        'evento/preview_evento.html',
        evento=evento,
        sorted_keys=sorted_keys,
        grouped_oficinas=grouped_oficinas
    )

@evento_routes.route('/criar_evento', methods=['GET', 'POST'])
@login_required
def criar_evento():
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))

    # Para evitar o erro 'evento is undefined' no template
    evento = None

    config_cli = ConfiguracaoCliente.query.filter_by(cliente_id=current_user.id).first()

    if request.method == 'POST':
        count_ev = Evento.query.filter_by(cliente_id=current_user.id).count()
        if config_cli and config_cli.limite_eventos is not None and count_ev >= config_cli.limite_eventos:
            flash('Limite de eventos atingido.', 'danger')
            return redirect(url_for('dashboard_routes.dashboard_cliente'))

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
            banner_url = url_for('static', filename=f'banners/{filename}', _external=False)
        
        # Processar campos de data
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')
        hora_inicio_str = request.form.get('hora_inicio')
        hora_fim_str = request.form.get('hora_fim')
        
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d') if data_inicio_str else None
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d') if data_fim_str else None
        
        from datetime import time
        hora_inicio = time.fromisoformat(hora_inicio_str) if hora_inicio_str else None
        hora_fim = time.fromisoformat(hora_fim_str) if hora_fim_str else None
        
        # Verificar se é gratuito
        inscricao_gratuita_val = request.form.get('inscricao_gratuita')
        inscricao_gratuita = inscricao_gratuita_val in ['on', '1', 'true']

        # Verificar se habilita lotes
        habilitar_lotes_val = request.form.get('habilitar_lotes')
        habilitar_lotes = habilitar_lotes_val in ['on', '1', 'true']
    
        # Cria o objeto Evento
        novo_evento = Evento(
            cliente_id=current_user.id,
            nome=nome,
            descricao=descricao,
            programacao=programacao,
            localizacao=localizacao,
            link_mapa=link_mapa,
            banner_url=banner_url,
            data_inicio=data_inicio,
            data_fim=data_fim,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            inscricao_gratuita=inscricao_gratuita,  # Salvar a flag no evento
            habilitar_lotes=habilitar_lotes  # Nova flag para habilitar lotes
        )

        try:
            db.session.add(novo_evento)
            db.session.flush()  # precisamos do ID para criar tipos de inscrição

            # Tratar tipos de inscrição
            nomes_tipos = request.form.getlist('nome_tipo[]')
            precos = request.form.getlist('preco_tipo[]')

            # Verificar se os tipos de inscrição foram fornecidos
            if not nomes_tipos:
                raise ValueError("É necessário definir pelo menos um tipo de inscrição.")

            # Para eventos gratuitos, definir todos os preços como 0.00
            if inscricao_gratuita:
                precos = ['0.00'] * len(nomes_tipos)

            # Criar tipos de inscrição para o evento
            tipos_inscricao = []
            for i, nome in enumerate(nomes_tipos):
                if nome.strip():  # Só criar se o nome não estiver vazio
                    preco_tipo = precos[i] if i < len(precos) else ''
                    preco_tipo = preco_tipo.strip() if preco_tipo else ''
                    preco = 0.0 if inscricao_gratuita or preco_tipo == '' else float(preco_tipo)
                    novo_tipo = EventoInscricaoTipo(
                        evento_id=novo_evento.id,
                        nome=nome,
                        preco=preco
                    )
                    db.session.add(novo_tipo)
                    db.session.flush()  # Para obter o ID do tipo
                    tipos_inscricao.append(novo_tipo)

            # Processar os lotes de inscrição somente se habilitar_lotes for True
            if habilitar_lotes:
                lote_nomes = request.form.getlist('lote_nome[]')
                lote_ordens = request.form.getlist('lote_ordem[]')
                lote_usar_data = [item == 'on' for item in request.form.getlist('lote_usar_data[]')]
                lote_data_inicio = request.form.getlist('lote_data_inicio[]')
                lote_data_fim = request.form.getlist('lote_data_fim[]')
                lote_usar_qtd = [item == 'on' for item in request.form.getlist('lote_usar_qtd[]')]
                lote_qtd_maxima = request.form.getlist('lote_qtd_maxima[]')

                # Criar cada lote
                for i, nome in enumerate(lote_nomes):
                    if nome.strip():
                        # Determinar se usa data ou quantidade
                        data_inicio_lote = None
                        data_fim_lote = None
                        qtd_maxima = None

                        if i < len(lote_usar_data) and lote_usar_data[i]:
                            if i < len(lote_data_inicio) and lote_data_inicio[i]:
                                data_inicio_lote = datetime.strptime(lote_data_inicio[i], '%Y-%m-%d')
                            if i < len(lote_data_fim) and lote_data_fim[i]:
                                data_fim_lote = datetime.strptime(lote_data_fim[i], '%Y-%m-%d')

                        if i < len(lote_usar_qtd) and lote_usar_qtd[i]:
                            if i < len(lote_qtd_maxima) and lote_qtd_maxima[i]:
                                qtd_maxima = int(lote_qtd_maxima[i])

                        # Criar o lote
                        novo_lote = LoteInscricao(
                            evento_id=novo_evento.id,
                            nome=nome,
                            data_inicio=data_inicio_lote,
                            data_fim=data_fim_lote,
                            qtd_maxima=qtd_maxima,
                            ordem=int(lote_ordens[i]) if i < len(lote_ordens) and lote_ordens[i] else i+1,
                            ativo=True
                        )
                        db.session.add(novo_lote)
                        db.session.flush()  # Para obter o ID do lote

                        # Processar preços por tipo de inscrição para este lote
                        for j, tipo in enumerate(tipos_inscricao):

                            # O formato do name é lote_tipo_preco_0_1 onde 0 é o índice do lote e 1 é o índice do tipo
                            preco_key = f'lote_tipo_preco_{i}_{j}'
                            preco_lote = request.form.get(preco_key)

                            if preco_lote:
                                preco_lote = preco_lote.strip()
                                # Se o evento for gratuito ou o valor estiver vazio, usar 0
                                preco_valor = 0.0 if inscricao_gratuita or preco_lote == '' else float(preco_lote)

                            # O formato do campo pode ser lote_tipo_preco_0_1 ou lote_tipo_preco_new_0_new_1
                            preco_key_num = f'lote_tipo_preco_{i}_{j}'
                            preco_key_new = f'lote_tipo_preco_new_{i}_new_{j}'
                            preco_lote_str = request.form.get(preco_key_num)
                            if preco_lote_str is None:
                                preco_lote_str = request.form.get(preco_key_new)

                            if preco_lote_str:
                                # Se o evento for gratuito, todos os preços são 0
                                preco_valor = 0.0 if inscricao_gratuita else float(preco_lote_str)


                                novo_preco = LoteTipoInscricao(
                                    lote_id=novo_lote.id,
                                    tipo_inscricao_id=tipo.id,
                                    preco=preco_valor
                                )
                                db.session.add(novo_preco)
            
            db.session.commit()
            flash('Evento criado com sucesso!', 'success')
            flash('Agora você pode configurar as regras de inscrição para este evento.', 'info')
            return redirect(url_for('dashboard_routes.dashboard_cliente'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar evento: {str(e)}', 'danger')

    # Retorna ao template, passando o 'evento' mesmo que seja None
    return render_template('evento/criar_evento.html', evento=evento)

@evento_routes.route('/evento/<identifier>')
def pagina_evento(identifier):
    evento = Evento.query.filter_by(token=identifier).first_or_404()

    oficinas = Oficina.query.filter_by(evento_id=evento.id).order_by(Oficina.data, Oficina.horario_inicio).all()

    # Agrupando oficinas por data
    from collections import defaultdict
    grouped_oficinas = defaultdict(list)
    ministrantes_set = set()

    for oficina in oficinas:
        data_str = oficina.data.strftime('%d/%m/%Y')
        grouped_oficinas[data_str].append(oficina)
        if oficina.ministrante:
            ministrantes_set.add(oficina.ministrante)

    sorted_keys = sorted(grouped_oficinas.keys(), key=lambda date: datetime.strptime(date, '%d/%m/%Y'))

    # Garante que estamos enviando uma lista e não um conjunto
    ministrantes = list(ministrantes_set)

    return render_template(
        'pagina_evento.html',
        evento=evento,
        grouped_oficinas=grouped_oficinas,
        sorted_keys=sorted_keys,
        ministrantes=ministrantes  # Passa os ministrantes para o template
    )


@evento_routes.route('/detalhes_evento/<int:evento_id>', methods=['GET'])
@login_required
def detalhes_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)

    # Carrega as oficinas associadas ao evento
    oficinas = Oficina.query.filter_by(evento_id=evento_id).order_by(Oficina.titulo).all()

    return render_template('professor/detalhes_evento.html', evento=evento, oficinas=oficinas)


# ---------------------------------------------------------------------------
# Novo: listagem e arquivamento de eventos do cliente
# ---------------------------------------------------------------------------

@evento_routes.route('/meus_eventos')
@login_required
def meus_eventos():
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))

    eventos = Evento.query.filter_by(cliente_id=current_user.id).order_by(Evento.data_inicio.desc()).all()
    return render_template('evento/meus_eventos.html', eventos=eventos)


@evento_routes.route('/toggle_arquivamento/<int:evento_id>', methods=['POST'])
@login_required
def toggle_arquivamento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    if current_user.tipo != 'cliente' or evento.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('evento_routes.meus_eventos'))

    novo_status = 'arquivado' if evento.status == 'ativo' else 'ativo'
    evento.status = novo_status
    db.session.commit()

    flash(f"Evento {'arquivado' if novo_status == 'arquivado' else 'reativado'} com sucesso!", 'success')
    return redirect(url_for('evento_routes.meus_eventos'))
