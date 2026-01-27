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
    current_app
)
from flask_login import login_required, current_user
from extensions import db
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import json
from io import BytesIO
import logging

from models import (
    Evento,
    Usuario,
    Submission,
)
from models.voting import (
    VotingEvent,
    VotingCategory,
    VotingQuestion,
    VotingWork,
    VotingAssignment,
    VotingVote,
    VotingResponse,
    VotingResult,
    VotingAuditLog,
)

logger = logging.getLogger(__name__)

# Criar blueprint para rotas de votação
voting_routes = Blueprint('voting_routes', __name__, url_prefix='/voting')


# =============================================================================
# ROTAS DE CONFIGURAÇÃO (CLIENTE)
# =============================================================================

@voting_routes.route('/configurar/<int:evento_id>')
@login_required
def configurar_votacao(evento_id):
    """Página principal de configuração de votação para um evento."""
    if current_user.tipo not in ['cliente', 'admin']:
        flash("Acesso negado. Apenas clientes podem configurar votações.", "error")
        return redirect(url_for('dashboard_routes.dashboard_cliente'))
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first_or_404()
    
    # Buscar evento de votação existente ou criar um novo
    voting_event = VotingEvent.query.filter_by(evento_id=evento_id).first()
    
    # Buscar trabalhos disponíveis para votação
    trabalhos_disponiveis = Submission.query.filter_by(evento_id=evento_id).all()
    
    # Buscar revisores disponíveis
    revisores_disponiveis = Usuario.query.filter_by(tipo='revisor').all()
    
    return render_template(
        'voting/configurar_votacao.html',
        evento=evento,
        voting_event=voting_event,
        trabalhos_disponiveis=trabalhos_disponiveis,
        revisores_disponiveis=revisores_disponiveis
    )


@voting_routes.route('/criar_evento_votacao', methods=['POST'])
@login_required
def criar_evento_votacao():
    """Cria um novo evento de votação."""
    if current_user.tipo not in ['cliente', 'admin']:
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        evento_id = data.get('evento_id')
        
        if not evento_id:
            return jsonify({'success': False, 'message': 'Evento não especificado'}), 400
        
        # Verificar se o evento pertence ao cliente
        evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
        if not evento:
            return jsonify({'success': False, 'message': 'Evento não encontrado'}), 404
        
        # Verificar se já existe um evento de votação
        existing_voting = VotingEvent.query.filter_by(evento_id=evento_id).first()
        if existing_voting:
            return jsonify({'success': False, 'message': 'Já existe um evento de votação para este evento'}), 400
        
        # Criar evento de votação
        voting_event = VotingEvent(
            cliente_id=current_user.id,
            evento_id=evento_id,
            nome=data.get('nome', f'Votação - {evento.nome}'),
            descricao=data.get('descricao', ''),
            data_inicio_votacao=datetime.fromisoformat(data['data_inicio']) if data.get('data_inicio') else None,
            data_fim_votacao=datetime.fromisoformat(data['data_fim']) if data.get('data_fim') else None,
            exibir_resultados_tempo_real=data.get('exibir_resultados_tempo_real', True),
            modo_revelacao=data.get('modo_revelacao', 'imediato'),
            permitir_votacao_multipla=data.get('permitir_votacao_multipla', False),
            exigir_login_revisor=data.get('exigir_login_revisor', True),
            permitir_voto_anonimo=data.get('permitir_voto_anonimo', False)
        )
        
        db.session.add(voting_event)
        db.session.commit()
        
        # Log de auditoria
        audit_log = VotingAuditLog(
            voting_event_id=voting_event.id,
            usuario_id=current_user.id,
            acao='criar_evento_votacao',
            detalhes={'evento_id': evento_id, 'nome': voting_event.nome},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Evento de votação criado com sucesso',
            'voting_event_id': voting_event.id
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar evento de votação: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@voting_routes.route('/categoria/<int:voting_event_id>', methods=['GET', 'POST'])
@login_required
def gerenciar_categorias(voting_event_id):
    """Gerencia categorias de votação."""
    if current_user.tipo not in ['cliente', 'admin']:
        flash("Acesso negado.", "error")
        return redirect(url_for('dashboard_routes.dashboard_cliente'))
    
    voting_event = VotingEvent.query.filter_by(
        id=voting_event_id, 
        cliente_id=current_user.id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            action = data.get('action')
            
            if action == 'criar':
                categoria = VotingCategory(
                    voting_event_id=voting_event_id,
                    nome=data['nome'],
                    descricao=data.get('descricao', ''),
                    ordem=data.get('ordem', 0),
                    pontuacao_minima=data.get('pontuacao_minima', 0.0),
                    pontuacao_maxima=data.get('pontuacao_maxima', 10.0),
                    tipo_pontuacao=data.get('tipo_pontuacao', 'numerica')
                )
                db.session.add(categoria)
                
            elif action == 'editar':
                categoria = VotingCategory.query.get(data['id'])
                if categoria and categoria.voting_event_id == voting_event_id:
                    categoria.nome = data['nome']
                    categoria.descricao = data.get('descricao', '')
                    categoria.ordem = data.get('ordem', 0)
                    categoria.pontuacao_minima = data.get('pontuacao_minima', 0.0)
                    categoria.pontuacao_maxima = data.get('pontuacao_maxima', 10.0)
                    categoria.tipo_pontuacao = data.get('tipo_pontuacao', 'numerica')
                
            elif action == 'deletar':
                categoria = VotingCategory.query.get(data['id'])
                if categoria and categoria.voting_event_id == voting_event_id:
                    db.session.delete(categoria)
            
            db.session.commit()
            
            # Log de auditoria
            audit_log = VotingAuditLog(
                voting_event_id=voting_event_id,
                usuario_id=current_user.id,
                acao=f'gerenciar_categorias_{action}',
                detalhes=data,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(audit_log)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Operação realizada com sucesso'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao gerenciar categorias: {e}")
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
    
    # GET - Listar categorias
    categorias = VotingCategory.query.filter_by(voting_event_id=voting_event_id).order_by(VotingCategory.ordem).all()
    
    return render_template(
        'voting/gerenciar_categorias.html',
        voting_event=voting_event,
        categorias=categorias
    )


@voting_routes.route('/perguntas/<int:categoria_id>', methods=['GET', 'POST'])
@login_required
def gerenciar_perguntas(categoria_id):
    """Gerencia perguntas de uma categoria."""
    categoria = VotingCategory.query.get_or_404(categoria_id)
    
    if current_user.tipo not in ['cliente', 'admin'] or categoria.voting_event.cliente_id != current_user.id:
        flash("Acesso negado.", "error")
        return redirect(url_for('dashboard_routes.dashboard_cliente'))
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            action = data.get('action')
            
            if action == 'criar':
                pergunta = VotingQuestion(
                    category_id=categoria_id,
                    texto_pergunta=data['texto_pergunta'],
                    observacao_explicativa=data.get('observacao_explicativa', ''),
                    ordem=data.get('ordem', 0),
                    obrigatoria=data.get('obrigatoria', True),
                    tipo_resposta=data.get('tipo_resposta', 'numerica'),
                    opcoes_resposta=data.get('opcoes_resposta'),
                    valor_minimo=data.get('valor_minimo'),
                    valor_maximo=data.get('valor_maximo'),
                    casas_decimais=data.get('casas_decimais', 1)
                )
                db.session.add(pergunta)
                
            elif action == 'editar':
                pergunta = VotingQuestion.query.get(data['id'])
                if pergunta and pergunta.category_id == categoria_id:
                    pergunta.texto_pergunta = data['texto_pergunta']
                    pergunta.observacao_explicativa = data.get('observacao_explicativa', '')
                    pergunta.ordem = data.get('ordem', 0)
                    pergunta.obrigatoria = data.get('obrigatoria', True)
                    pergunta.tipo_resposta = data.get('tipo_resposta', 'numerica')
                    pergunta.opcoes_resposta = data.get('opcoes_resposta')
                    pergunta.valor_minimo = data.get('valor_minimo')
                    pergunta.valor_maximo = data.get('valor_maximo')
                    pergunta.casas_decimais = data.get('casas_decimais', 1)
                
            elif action == 'deletar':
                pergunta = VotingQuestion.query.get(data['id'])
                if pergunta and pergunta.category_id == categoria_id:
                    db.session.delete(pergunta)
            
            db.session.commit()
            
            # Log de auditoria
            audit_log = VotingAuditLog(
                voting_event_id=categoria.voting_event_id,
                usuario_id=current_user.id,
                acao=f'gerenciar_perguntas_{action}',
                detalhes=data,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(audit_log)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Operação realizada com sucesso'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao gerenciar perguntas: {e}")
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
    
    # GET - Listar perguntas
    perguntas = VotingQuestion.query.filter_by(category_id=categoria_id).order_by(VotingQuestion.ordem).all()
    
    return render_template(
        'voting/gerenciar_perguntas.html',
        categoria=categoria,
        perguntas=perguntas
    )


@voting_routes.route('/trabalhos/<int:voting_event_id>', methods=['GET', 'POST'])
@login_required
def gerenciar_trabalhos(voting_event_id):
    """Gerencia trabalhos participantes da votação."""
    voting_event = VotingEvent.query.filter_by(
        id=voting_event_id, 
        cliente_id=current_user.id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            action = data.get('action')
            
            if action == 'adicionar_trabalho':
                # Buscar submission existente
                submission = Submission.query.get(data['submission_id'])
                if not submission:
                    return jsonify({'success': False, 'message': 'Trabalho não encontrado'}), 404
                
                # Verificar se já está na votação
                existing_work = VotingWork.query.filter_by(
                    voting_event_id=voting_event_id,
                    submission_id=data['submission_id']
                ).first()
                
                if existing_work:
                    return jsonify({'success': False, 'message': 'Trabalho já está na votação'}), 400
                
                # Criar trabalho na votação
                work = VotingWork(
                    voting_event_id=voting_event_id,
                    submission_id=data['submission_id'],
                    titulo=submission.title,
                    resumo=submission.abstract,
                    autores=data.get('autores', ''),
                    categoria_original=data.get('categoria_original', ''),
                    ordem_exibicao=data.get('ordem_exibicao', 0)
                )
                db.session.add(work)
                
            elif action == 'importar_todos':
                # Importar todos os trabalhos do evento
                submissions = Submission.query.filter_by(evento_id=voting_event.evento_id).all()
                imported_count = 0
                
                for submission in submissions:
                    existing_work = VotingWork.query.filter_by(
                        voting_event_id=voting_event_id,
                        submission_id=submission.id
                    ).first()
                    
                    if not existing_work:
                        work = VotingWork(
                            voting_event_id=voting_event_id,
                            submission_id=submission.id,
                            titulo=submission.title,
                            resumo=submission.abstract,
                            autores='',
                            categoria_original='',
                            ordem_exibicao=imported_count
                        )
                        db.session.add(work)
                        imported_count += 1
                
            elif action == 'editar':
                work = VotingWork.query.get(data['id'])
                if work and work.voting_event_id == voting_event_id:
                    work.titulo = data.get('titulo', work.titulo)
                    work.resumo = data.get('resumo', work.resumo)
                    work.autores = data.get('autores', work.autores)
                    work.categoria_original = data.get('categoria_original', work.categoria_original)
                    work.ordem_exibicao = data.get('ordem_exibicao', work.ordem_exibicao)
                    work.ativo = data.get('ativo', work.ativo)
                
            elif action == 'remover':
                work = VotingWork.query.get(data['id'])
                if work and work.voting_event_id == voting_event_id:
                    db.session.delete(work)
            
            db.session.commit()
            
            # Log de auditoria
            audit_log = VotingAuditLog(
                voting_event_id=voting_event_id,
                usuario_id=current_user.id,
                acao=f'gerenciar_trabalhos_{action}',
                detalhes=data,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(audit_log)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Operação realizada com sucesso'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao gerenciar trabalhos: {e}")
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
    
    # GET - Listar trabalhos
    trabalhos = VotingWork.query.filter_by(voting_event_id=voting_event_id).order_by(VotingWork.ordem_exibicao).all()
    trabalhos_disponiveis = Submission.query.filter_by(evento_id=voting_event.evento_id).all()
    
    return render_template(
        'voting/gerenciar_trabalhos.html',
        voting_event=voting_event,
        trabalhos=trabalhos,
        trabalhos_disponiveis=trabalhos_disponiveis
    )


@voting_routes.route('/atribuir_revisores/<int:voting_event_id>', methods=['GET', 'POST'])
@login_required
def atribuir_revisores(voting_event_id):
    """Atribui trabalhos para revisores votarem."""
    voting_event = VotingEvent.query.filter_by(
        id=voting_event_id, 
        cliente_id=current_user.id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            action = data.get('action')
            
            if action == 'atribuir':
                # Atribuir trabalho específico para revisor
                assignment = VotingAssignment(
                    voting_event_id=voting_event_id,
                    revisor_id=data['revisor_id'],
                    work_id=data['work_id'],
                    prazo_votacao=datetime.fromisoformat(data['prazo_votacao']) if data.get('prazo_votacao') else None
                )
                db.session.add(assignment)
                
            elif action == 'atribuir_todos':
                # Atribuir todos os trabalhos para todos os revisores
                revisores = data.get('revisores', [])
                trabalhos = VotingWork.query.filter_by(voting_event_id=voting_event_id, ativo=True).all()
                
                for revisor_id in revisores:
                    for trabalho in trabalhos:
                        # Verificar se já existe atribuição
                        existing = VotingAssignment.query.filter_by(
                            voting_event_id=voting_event_id,
                            revisor_id=revisor_id,
                            work_id=trabalho.id
                        ).first()
                        
                        if not existing:
                            assignment = VotingAssignment(
                                voting_event_id=voting_event_id,
                                revisor_id=revisor_id,
                                work_id=trabalho.id,
                                prazo_votacao=datetime.fromisoformat(data['prazo_votacao']) if data.get('prazo_votacao') else None
                            )
                            db.session.add(assignment)
                
            elif action == 'remover':
                assignment = VotingAssignment.query.get(data['id'])
                if assignment and assignment.voting_event_id == voting_event_id:
                    db.session.delete(assignment)
            
            db.session.commit()
            
            # Log de auditoria
            audit_log = VotingAuditLog(
                voting_event_id=voting_event_id,
                usuario_id=current_user.id,
                acao=f'atribuir_revisores_{action}',
                detalhes=data,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(audit_log)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Operação realizada com sucesso'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atribuir revisores: {e}")
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
    
    # GET - Listar atribuições
    atribuicoes = VotingAssignment.query.filter_by(voting_event_id=voting_event_id).all()
    revisores_disponiveis = Usuario.query.filter_by(tipo='revisor').all()
    trabalhos = VotingWork.query.filter_by(voting_event_id=voting_event_id, ativo=True).all()
    
    return render_template(
        'voting/atribuir_revisores.html',
        voting_event=voting_event,
        atribuicoes=atribuicoes,
        revisores_disponiveis=revisores_disponiveis,
        trabalhos=trabalhos
    )


# =============================================================================
# ROTAS DE VOTAÇÃO (REVISORES)
# =============================================================================

@voting_routes.route('/painel_revisor')
@login_required
def painel_revisor():
    """Painel do revisor com trabalhos atribuídos para votação."""
    if current_user.tipo not in ['revisor', 'admin']:
        flash("Acesso negado. Apenas revisores podem votar.", "error")
        return redirect(url_for('dashboard_routes.dashboard'))
    
    # Buscar atribuições do revisor
    atribuicoes = VotingAssignment.query.filter_by(revisor_id=current_user.id).all()
    
    # Separar por status
    pendentes = []
    concluidas = []
    
    for atribuicao in atribuicoes:
        if atribuicao.concluida:
            concluidas.append(atribuicao)
        else:
            pendentes.append(atribuicao)
    
    return render_template(
        'voting/painel_revisor.html',
        atribuicoes_pendentes=pendentes,
        atribuicoes_concluidas=concluidas
    )


@voting_routes.route('/votar/<int:assignment_id>')
@login_required
def votar(assignment_id):
    """Interface de votação para um trabalho específico."""
    if current_user.tipo not in ['revisor', 'admin']:
        flash("Acesso negado.", "error")
        return redirect(url_for('voting_routes.painel_revisor'))
    
    atribuicao = VotingAssignment.query.get_or_404(assignment_id)
    
    # Verificar se o revisor tem acesso
    if atribuicao.revisor_id != current_user.id:
        flash("Acesso negado a este trabalho.", "error")
        return redirect(url_for('voting_routes.painel_revisor'))
    
    # Verificar se a votação está ativa
    if not atribuicao.voting_event.is_active:
        flash("Votação não está ativa.", "error")
        return redirect(url_for('voting_routes.painel_revisor'))
    
    # Buscar categorias e perguntas
    categorias = VotingCategory.query.filter_by(
        voting_event_id=atribuicao.voting_event_id,
        ativa=True
    ).order_by(VotingCategory.ordem).all()
    
    # Buscar votos existentes
    votos_existentes = VotingVote.query.filter_by(
        voting_event_id=atribuicao.voting_event_id,
        work_id=atribuicao.work_id,
        revisor_id=current_user.id
    ).all()
    
    return render_template(
        'voting/votar.html',
        atribuicao=atribuicao,
        categorias=categorias,
        votos_existentes=votos_existentes
    )


@voting_routes.route('/salvar_voto', methods=['POST'])
@login_required
def salvar_voto():
    """Salva o voto do revisor."""
    if current_user.tipo not in ['revisor', 'admin']:
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        voting_event_id = data.get('voting_event_id')
        work_id = data.get('work_id')
        category_id = data.get('category_id')
        
        # Verificar se já existe voto
        existing_vote = VotingVote.query.filter_by(
            voting_event_id=voting_event_id,
            work_id=work_id,
            category_id=category_id,
            revisor_id=current_user.id
        ).first()
        
        if existing_vote:
            # Atualizar voto existente
            vote = existing_vote
            # Remover respostas antigas
            VotingResponse.query.filter_by(vote_id=vote.id).delete()
        else:
            # Criar novo voto
            vote = VotingVote(
                voting_event_id=voting_event_id,
                category_id=category_id,
                work_id=work_id,
                revisor_id=current_user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(vote)
            db.session.flush()  # Para obter o ID
        
        # Processar respostas
        respostas = data.get('respostas', [])
        pontuacao_total = 0
        
        for resposta_data in respostas:
            resposta = VotingResponse(
                vote_id=vote.id,
                question_id=resposta_data['question_id'],
                valor_numerico=resposta_data.get('valor_numerico'),
                texto_resposta=resposta_data.get('texto_resposta'),
                opcoes_selecionadas=resposta_data.get('opcoes_selecionadas')
            )
            db.session.add(resposta)
            
            # Somar pontuação se for numérica
            if resposta_data.get('valor_numerico'):
                pontuacao_total += float(resposta_data['valor_numerico'])
        
        # Atualizar pontuação final
        vote.pontuacao_final = pontuacao_total
        vote.observacoes = data.get('observacoes', '')
        
        db.session.commit()
        
        # Log de auditoria
        audit_log = VotingAuditLog(
            voting_event_id=voting_event_id,
            usuario_id=current_user.id,
            acao='salvar_voto',
            detalhes={
                'work_id': work_id,
                'category_id': category_id,
                'pontuacao_final': pontuacao_total
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Voto salvo com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar voto: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@voting_routes.route('/finalizar_votacao/<int:assignment_id>', methods=['POST'])
@login_required
def finalizar_votacao(assignment_id):
    """Finaliza a votação de um trabalho."""
    if current_user.tipo not in ['revisor', 'admin']:
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        atribuicao = VotingAssignment.query.get_or_404(assignment_id)
        
        if atribuicao.revisor_id != current_user.id:
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        
        # Marcar como concluída
        atribuicao.concluida = True
        atribuicao.data_conclusao = datetime.utcnow()
        
        db.session.commit()
        
        # Log de auditoria
        audit_log = VotingAuditLog(
            voting_event_id=atribuicao.voting_event_id,
            usuario_id=current_user.id,
            acao='finalizar_votacao',
            detalhes={'assignment_id': assignment_id},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Votação finalizada com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao finalizar votação: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


# =============================================================================
# ROTAS DE RESULTADOS
# =============================================================================

@voting_routes.route('/resultados/<int:voting_event_id>')
@login_required
def resultados(voting_event_id):
    """Exibe resultados da votação."""
    voting_event = VotingEvent.query.get_or_404(voting_event_id)
    
    # Verificar permissões
    if current_user.tipo not in ['cliente', 'admin']:
        flash("Acesso negado.", "error")
        return redirect(url_for('dashboard_routes.dashboard'))
    
    if voting_event.cliente_id != current_user.id:
        flash("Acesso negado a este evento.", "error")
        return redirect(url_for('dashboard_routes.dashboard_cliente'))
    
    # Calcular resultados se necessário
    _calcular_resultados(voting_event_id)
    
    # Buscar resultados
    resultados = VotingResult.query.filter_by(voting_event_id=voting_event_id).all()
    categorias = VotingCategory.query.filter_by(voting_event_id=voting_event_id, ativa=True).all()
    
    # Organizar resultados por categoria
    resultados_por_categoria = {}
    for categoria in categorias:
        resultados_categoria = [r for r in resultados if r.category_id == categoria.id]
        resultados_categoria.sort(key=lambda x: x.pontuacao_total, reverse=True)
        resultados_por_categoria[categoria.id] = {
            'categoria': categoria,
            'resultados': resultados_categoria
        }
    
    return render_template(
        'voting/resultados.html',
        voting_event=voting_event,
        resultados_por_categoria=resultados_por_categoria
    )


@voting_routes.route('/resultados_tempo_real/<int:voting_event_id>')
def resultados_tempo_real(voting_event_id):
    """API para resultados em tempo real."""
    voting_event = VotingEvent.query.get_or_404(voting_event_id)
    
    if not voting_event.exibir_resultados_tempo_real:
        return jsonify({'error': 'Resultados em tempo real não habilitados'}), 403
    
    # Calcular resultados
    _calcular_resultados(voting_event_id)
    
    # Buscar resultados atualizados
    resultados = VotingResult.query.filter_by(voting_event_id=voting_event_id).all()
    categorias = VotingCategory.query.filter_by(voting_event_id=voting_event_id, ativa=True).all()
    
    # Organizar dados para JSON
    dados_resultados = {}
    for categoria in categorias:
        resultados_categoria = [r for r in resultados if r.category_id == categoria.id]
        resultados_categoria.sort(key=lambda x: x.pontuacao_total, reverse=True)
        
        dados_resultados[categoria.id] = {
            'nome': categoria.nome,
            'resultados': [
                {
                    'work_id': r.work_id,
                    'titulo': r.work.titulo,
                    'pontuacao_total': r.pontuacao_total,
                    'pontuacao_media': r.pontuacao_media,
                    'numero_votos': r.numero_votos,
                    'posicao_ranking': r.posicao_ranking
                }
                for r in resultados_categoria
            ]
        }
    
    return jsonify(dados_resultados)


@voting_routes.route('/exportar_resultados/<int:voting_event_id>/<string:formato>')
@login_required
def exportar_resultados(voting_event_id, formato):
    """Exporta resultados em PDF ou Excel."""
    voting_event = VotingEvent.query.get_or_404(voting_event_id)
    
    if current_user.tipo not in ['cliente', 'admin'] or voting_event.cliente_id != current_user.id:
        abort(403)
    
    # Calcular resultados
    _calcular_resultados(voting_event_id)
    
    # Buscar dados
    resultados = VotingResult.query.filter_by(voting_event_id=voting_event_id).all()
    categorias = VotingCategory.query.filter_by(voting_event_id=voting_event_id, ativa=True).all()
    
    if formato.lower() == 'pdf':
        return _exportar_resultados_pdf(voting_event, resultados, categorias)
    elif formato.lower() == 'xlsx':
        return _exportar_resultados_xlsx(voting_event, resultados, categorias)
    else:
        abort(400)


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def _calcular_resultados(voting_event_id):
    """Calcula e atualiza resultados da votação."""
    try:
        # Buscar todos os votos
        votos = VotingVote.query.filter_by(voting_event_id=voting_event_id).all()
        
        # Agrupar por categoria e trabalho
        votos_agrupados = {}
        for voto in votos:
            key = (voto.category_id, voto.work_id)
            if key not in votos_agrupados:
                votos_agrupados[key] = []
            votos_agrupados[key].append(voto)
        
        # Calcular resultados
        for (category_id, work_id), votos_grupo in votos_agrupados.items():
            pontuacoes = [v.pontuacao_final for v in votos_grupo if v.pontuacao_final is not None]
            
            if pontuacoes:
                pontuacao_total = sum(pontuacoes)
                pontuacao_media = pontuacao_total / len(pontuacoes)
                numero_votos = len(pontuacoes)
                
                # Buscar ou criar resultado
                resultado = VotingResult.query.filter_by(
                    voting_event_id=voting_event_id,
                    category_id=category_id,
                    work_id=work_id
                ).first()
                
                if not resultado:
                    resultado = VotingResult(
                        voting_event_id=voting_event_id,
                        category_id=category_id,
                        work_id=work_id
                    )
                    db.session.add(resultado)
                
                resultado.pontuacao_total = pontuacao_total
                resultado.pontuacao_media = pontuacao_media
                resultado.numero_votos = numero_votos
        
        # Calcular rankings
        categorias = VotingCategory.query.filter_by(voting_event_id=voting_event_id, ativa=True).all()
        for categoria in categorias:
            resultados_categoria = VotingResult.query.filter_by(
                voting_event_id=voting_event_id,
                category_id=categoria.id
            ).order_by(desc(VotingResult.pontuacao_total)).all()
            
            for posicao, resultado in enumerate(resultados_categoria, 1):
                resultado.posicao_ranking = posicao
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao calcular resultados: {e}")


def _exportar_resultados_pdf(voting_event, resultados, categorias):
    """Exporta resultados em PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, title=f'Resultados - {voting_event.nome}')
        
        styles = getSampleStyleSheet()
        elements = []
        
        # Título
        elements.append(Paragraph(f'Resultados da Votação: {voting_event.nome}', styles['Title']))
        elements.append(Spacer(1, 12))
        
        # Informações do evento
        elements.append(Paragraph(f'Evento: {voting_event.evento.nome}', styles['Normal']))
        elements.append(Paragraph(f'Data: {datetime.utcnow().strftime("%d/%m/%Y %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Resultados por categoria
        for categoria in categorias:
            elementos_categoria = [r for r in resultados if r.category_id == categoria.id]
            elementos_categoria.sort(key=lambda x: x.posicao_ranking or 999)
            
            elements.append(Paragraph(f'Categoria: {categoria.nome}', styles['Heading2']))
            elements.append(Spacer(1, 12))
            
            # Tabela de resultados
            if elementos_categoria:
                table_data = [['Posição', 'Trabalho', 'Pontuação Total', 'Pontuação Média', 'Número de Votos']]
                
                for resultado in elementos_categoria:
                    table_data.append([
                        str(resultado.posicao_ranking or '-'),
                        resultado.work.titulo,
                        f'{resultado.pontuacao_total:.2f}',
                        f'{resultado.pontuacao_media:.2f}',
                        str(resultado.numero_votos)
                    ])
                
                table = Table(table_data, colWidths=[60, 200, 100, 100, 100])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1d4ed8')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                elements.append(table)
            else:
                elements.append(Paragraph('Nenhum resultado disponível.', styles['Normal']))
            
            elements.append(Spacer(1, 20))
        
        doc.build(elements)
        buffer.seek(0)
        
        filename = f"resultados_votacao_{voting_event.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except ImportError:
        abort(500, description='Biblioteca ReportLab não disponível')


def _exportar_resultados_xlsx(voting_event, resultados, categorias):
    """Exporta resultados em Excel."""
    try:
        import xlsxwriter
        
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        header_format = workbook.add_format({'bold': True, 'bg_color': '#1d4ed8', 'font_color': 'white'})
        
        # Planilha de resumo
        summary_ws = workbook.add_worksheet('Resumo')
        summary_ws.write(0, 0, f'Resultados da Votação: {voting_event.nome}', header_format)
        summary_ws.write(1, 0, f'Evento: {voting_event.evento.nome}')
        summary_ws.write(2, 0, f'Data: {datetime.utcnow().strftime("%d/%m/%Y %H:%M")}')
        
        # Planilhas por categoria
        for categoria in categorias:
            elementos_categoria = [r for r in resultados if r.category_id == categoria.id]
            elementos_categoria.sort(key=lambda x: x.posicao_ranking or 999)
            
            ws = workbook.add_worksheet(categoria.nome[:31])  # Limite de 31 caracteres
            
            headers = ['Posição', 'Trabalho', 'Pontuação Total', 'Pontuação Média', 'Número de Votos']
            for col, header in enumerate(headers):
                ws.write(0, col, header, header_format)
            
            for row, resultado in enumerate(elementos_categoria, 1):
                ws.write(row, 0, resultado.posicao_ranking or '-')
                ws.write(row, 1, resultado.work.titulo)
                ws.write(row, 2, resultado.pontuacao_total)
                ws.write(row, 3, resultado.pontuacao_media)
                ws.write(row, 4, resultado.numero_votos)
        
        workbook.close()
        output.seek(0)
        
        filename = f"resultados_votacao_{voting_event.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except ImportError:
        abort(500, description='Biblioteca XLSXWriter não disponível')

