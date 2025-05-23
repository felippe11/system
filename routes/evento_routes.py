from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, cast, Date, func
from werkzeug.utils import secure_filename
from datetime import datetime
from collections import defaultdict
import os
from datetime import date


from extensions import db
from models import (
    Evento, Oficina, LinkCadastro, LoteInscricao, EventoInscricaoTipo,
    Usuario, RegraInscricaoEvento, LoteTipoInscricao, Inscricao
)

evento_routes = Blueprint('evento_routes', __name__)


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
        print(f"[ERRO] home(): {e}")
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
    
    # 2. Busca um link de cadastro para este evento
    link = LinkCadastro.query.filter_by(evento_id=evento_id).first()
    
    if link:
        # Se existe um link personalizado, usa ele
        if link.slug_customizado:
            return redirect(url_for('evento_routes.inscricao', slug=link.slug_customizado))
        # Senão, usa o token
        return redirect(url_for('evento_routes.cadastro_participante', token=link.token))
    
    # 3. Se não existe link, verifica se o evento permite inscrição direta
    if evento.publico and not evento.requer_aprovacao:
        # Aqui está a correção - não usamos mais link.token pois link é None
        # Criamos um token temporário ou usamos um método alternativo
        return redirect(url_for('evento_routes.cadastro_participante', evento_id=evento_id))
    
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
            'preco_base':  min((t.preco for t in ev.tipos_inscricao), default=0),
            'link_inscricao': None
        }

        # link de inscrição (se houver)
        if ev.links_cadastro:
            link = ev.links_cadastro[0]
            dado['link_inscricao'] = (
                url_for('evento_routes.abrir_inscricao_customizada', slug=link.slug_customizado)
                if link.slug_customizado else
                url_for('inscricao_routes.abrir_inscricao_token', token=link.token)  # Corrigido o blueprint
            )

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
                # adicione outros campos necessários para o template eventos.html
                'data_inicio': evento.data_inicio.strftime('%d/%m/%Y') if evento.data_inicio else 'Data a definir',
                'localizacao': evento.localizacao or 'Local a definir',
                'preco_base': 0
            }
            
            if evento.tipos_inscricao and len(evento.tipos_inscricao) > 0:
                evento_dict['preco_base'] = min(tipo.preco for tipo in evento.tipos_inscricao)
            
            eventos_processed.append(evento_dict)
        
        return render_template('eventos.html', eventos=eventos_processed)
    
    except Exception as e:
        print(f"Erro em listar_eventos: {str(e)}")
        return render_template('eventos.html', eventos=[])

@evento_routes.route('/configurar_evento', methods=['GET', 'POST'])
@login_required
def configurar_evento():
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('evento_routes.dashboard_cliente'))

    # Lista todos os eventos do cliente
    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    
    # Evento selecionado (por padrão, None até que o usuário escolha)
    evento_id = request.args.get('evento_id') or (request.form.get('evento_id') if request.method == 'POST' else None)
    evento = None
    if evento_id:
        # Carregamento eager de todos os relacionamentos necessários
        evento = Evento.query.options(
            db.joinedload(Evento.tipos_inscricao),
            db.joinedload(Evento.lotes).joinedload(LoteInscricao.tipos_inscricao)
        ).filter_by(id=evento_id, cliente_id=current_user.id).first()

    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        programacao = request.form.get('programacao')
        localizacao = request.form.get('localizacao')
        link_mapa = request.form.get('link_mapa')
        inscricao_gratuita = request.form.get('inscricao_gratuita') == 'on'  # Checkbox retorna 'on' se marcado
        habilitar_lotes = request.form.get('habilitar_lotes') == 'on'  # Novo campo
        nomes_tipos = request.form.getlist('nome_tipo[]')  # Lista de nomes dos tipos
        precos_tipos = request.form.getlist('preco_tipo[]')  # Lista de preços dos tipos
        
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
                for nome_tipo, preco_tipo in zip(nomes_tipos, precos_tipos):
                    if nome_tipo:  # Só adicionar se o nome for preenchido
                        # Se for inscrição gratuita, definir preço como 0.00
                        preco_efetivo = 0.0 if inscricao_gratuita else float(preco_tipo)
                        
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
                            tipos_inscricao.append(tipo_existente)
                        else:
                            # Cria um novo tipo
                            tipo = EventoInscricaoTipo(
                                evento_id=evento.id,
                                nome=nome_tipo,
                                preco=preco_efetivo
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
                                    # Se for gratuito, todos os preços são 0
                                    preco_final = 0.0 if inscricao_gratuita else float(preco_valor)
                                    
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
                    habilitar_lotes=habilitar_lotes  # Novo campo
                )
                db.session.add(evento)
                db.session.flush()  # Gera o ID do evento antes de adicionar os tipos

                # Adicionar tipos de inscrição
                tipos_inscricao = []
                for nome_tipo, preco_tipo in zip(nomes_tipos, precos_tipos):
                    if nome_tipo:  # Só adicionar se o nome for preenchido
                        # Se for inscrição gratuita, definir preço como 0.00
                        preco_efetivo = 0.0 if inscricao_gratuita else float(preco_tipo)
                        
                        tipo = EventoInscricaoTipo(
                            evento_id=evento.id,
                            nome=nome_tipo,
                            preco=preco_efetivo
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
                            for tipo in tipos_inscricao:
                                # Para novos lotes e tipos, o formato é diferente
                                preco_key = f'lote_tipo_preco_new_{i}_{tipo.id}'
                                # Verificar também o formato alternativo para compatibilidade
                                preco_valor = request.form.get(preco_key) or request.form.get(f'lote_tipo_preco_new_{i}_new_{j}')
                                
                                if preco_valor is not None:
                                    # Se for gratuito, todos os preços são 0
                                    preco_final = 0.0 if inscricao_gratuita else float(preco_valor)
                                    
                                    novo_lote_tipo = LoteTipoInscricao(
                                        lote_id=lote.id,
                                        tipo_inscricao_id=tipo.id,
                                        preco=preco_final
                                    )
                                    db.session.add(novo_lote_tipo)

            db.session.commit()
            
            # Recarregar o evento com todos os relacionamentos para exibição
            if evento:
                evento = Evento.query.options(
                    db.joinedload(Evento.tipos_inscricao),
                    db.joinedload(Evento.lotes).joinedload(LoteInscricao.tipos_inscricao)
                ).filter_by(id=evento.id, cliente_id=current_user.id).first()
                
            flash('Evento salvo com sucesso!', 'success')
            return redirect(url_for('evento_routes.dashboard_cliente'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar evento: {str(e)}', 'danger')
            # Adicionar log para debugging
            print(f"Erro ao salvar evento: {str(e)}")
            import traceback
            traceback.print_exc()

    return render_template(
    "configurar_evento.html",
    eventos=eventos,
    evento=evento,
    habilita_pagamento=current_user.habilita_pagamento   #  <-- acrescente isto
)

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

   # No trecho onde você monta grouped_oficinas
    for oficina in oficinas:
        for dia in oficina.dias:
            data_str = dia.data.strftime('%d/%m/%Y')
            temp_group[data_str].append({
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
        'exibir_evento.html',
        evento=evento,
        sorted_keys=sorted_keys,
        grouped_oficinas=grouped_oficinas
    )

@evento_routes.route('/criar_evento', methods=['GET', 'POST'])
@login_required
def criar_evento():
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('evento_routes.dashboard_cliente'))
    
    # Para evitar o erro 'evento is undefined' no template
    evento = None

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
        inscricao_gratuita = (request.form.get('inscricao_gratuita') == 'on')
        
        # Verificar se habilita lotes
        habilitar_lotes = (request.form.get('habilitar_lotes') == 'on')
    
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

            # Se o cliente tiver pagamento habilitado, tratar tipos de inscrição
            if current_user.habilita_pagamento:
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
                        preco = 0.0 if inscricao_gratuita else float(precos[i])
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
                                    # Se o evento for gratuito, todos os preços são 0
                                    preco_valor = 0.0 if inscricao_gratuita else float(preco_lote)
                                    
                                    novo_preco = LoteTipoInscricao(
                                        lote_id=novo_lote.id,
                                        tipo_inscricao_id=tipo.id,
                                        preco=preco_valor
                                    )
                                    db.session.add(novo_preco)
            
            db.session.commit()
            flash('Evento criado com sucesso!', 'success')
            flash('Agora você pode configurar as regras de inscrição para este evento.', 'info')
            return redirect(url_for('evento_routes.dashboard_cliente'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar evento: {str(e)}', 'danger')

    # Retorna ao template, passando o 'evento' mesmo que seja None
    return render_template('criar_evento.html', evento=evento)

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

    return render_template('detalhes_evento.html', evento=evento, oficinas=oficinas)