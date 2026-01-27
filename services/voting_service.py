"""
Serviço para gerenciar o sistema de votação.
"""

from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
import logging

from extensions import db
from models import Usuario, Evento, Submission
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


class VotingService:
    """Serviço para operações do sistema de votação."""
    
    @staticmethod
    def create_voting_event(cliente_id: int, evento_id: int, **kwargs) -> VotingEvent:
        """Cria um novo evento de votação."""
        try:
            voting_event = VotingEvent(
                cliente_id=cliente_id,
                evento_id=evento_id,
                nome=kwargs.get('nome', f'Votação - {Evento.query.get(evento_id).nome}'),
                descricao=kwargs.get('descricao', ''),
                data_inicio_votacao=kwargs.get('data_inicio_votacao'),
                data_fim_votacao=kwargs.get('data_fim_votacao'),
                exibir_resultados_tempo_real=kwargs.get('exibir_resultados_tempo_real', True),
                modo_revelacao=kwargs.get('modo_revelacao', 'imediato'),
                permitir_votacao_multipla=kwargs.get('permitir_votacao_multipla', False),
                exigir_login_revisor=kwargs.get('exigir_login_revisor', True),
                permitir_voto_anonimo=kwargs.get('permitir_voto_anonimo', False)
            )
            
            db.session.add(voting_event)
            db.session.commit()
            
            # Log de auditoria
            VotingService._log_audit(
                voting_event_id=voting_event.id,
                usuario_id=kwargs.get('usuario_id'),
                acao='criar_evento_votacao',
                detalhes=kwargs
            )
            
            return voting_event
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao criar evento de votação: {e}")
            raise
    
    @staticmethod
    def import_works_from_submissions(voting_event_id: int, submission_ids: List[int] = None) -> List[VotingWork]:
        """Importa trabalhos das submissões para a votação."""
        try:
            voting_event = VotingEvent.query.get(voting_event_id)
            if not voting_event:
                raise ValueError("Evento de votação não encontrado")
            
            # Buscar submissões do evento
            query = Submission.query.filter_by(evento_id=voting_event.evento_id)
            if submission_ids:
                query = query.filter(Submission.id.in_(submission_ids))
            
            submissions = query.all()
            imported_works = []
            
            for submission in submissions:
                # Verificar se já existe
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
                        ordem_exibicao=len(imported_works)
                    )
                    db.session.add(work)
                    imported_works.append(work)
            
            db.session.commit()
            return imported_works
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao importar trabalhos: {e}")
            raise
    
    @staticmethod
    def assign_works_to_reviewers(voting_event_id: int, revisor_ids: List[int], 
                                 work_ids: List[int] = None, prazo_votacao: datetime = None) -> List[VotingAssignment]:
        """Atribui trabalhos para revisores votarem."""
        try:
            voting_event = VotingEvent.query.get(voting_event_id)
            if not voting_event:
                raise ValueError("Evento de votação não encontrado")
            
            # Buscar trabalhos
            query = VotingWork.query.filter_by(voting_event_id=voting_event_id, ativo=True)
            if work_ids:
                query = query.filter(VotingWork.id.in_(work_ids))
            
            works = query.all()
            assignments = []
            
            for revisor_id in revisor_ids:
                for work in works:
                    # Verificar se já existe atribuição
                    existing = VotingAssignment.query.filter_by(
                        voting_event_id=voting_event_id,
                        revisor_id=revisor_id,
                        work_id=work.id
                    ).first()
                    
                    if not existing:
                        assignment = VotingAssignment(
                            voting_event_id=voting_event_id,
                            revisor_id=revisor_id,
                            work_id=work.id,
                            prazo_votacao=prazo_votacao
                        )
                        db.session.add(assignment)
                        assignments.append(assignment)
            
            db.session.commit()
            return assignments
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao atribuir trabalhos: {e}")
            raise
    
    @staticmethod
    def save_vote(voting_event_id: int, category_id: int, work_id: int, 
                  revisor_id: int, respostas: List[Dict], observacoes: str = '') -> VotingVote:
        """Salva o voto de um revisor."""
        try:
            # Verificar se já existe voto
            existing_vote = VotingVote.query.filter_by(
                voting_event_id=voting_event_id,
                category_id=category_id,
                work_id=work_id,
                revisor_id=revisor_id
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
                    revisor_id=revisor_id
                )
                db.session.add(vote)
                db.session.flush()  # Para obter o ID
            
            # Processar respostas
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
            vote.observacoes = observacoes
            
            db.session.commit()
            
            # Log de auditoria
            VotingService._log_audit(
                voting_event_id=voting_event_id,
                usuario_id=revisor_id,
                acao='salvar_voto',
                detalhes={
                    'category_id': category_id,
                    'work_id': work_id,
                    'pontuacao_final': pontuacao_total
                }
            )
            
            return vote
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar voto: {e}")
            raise
    
    @staticmethod
    def calculate_results(voting_event_id: int) -> List[VotingResult]:
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
            
            resultados = []
            
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
                    resultados.append(resultado)
            
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
            return resultados
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao calcular resultados: {e}")
            raise
    
    @staticmethod
    def get_reviewer_assignments(revisor_id: int) -> Tuple[List[VotingAssignment], List[VotingAssignment]]:
        """Busca atribuições de um revisor separadas por status."""
        try:
            atribuicoes = VotingAssignment.query.filter_by(revisor_id=revisor_id).all()
            
            pendentes = []
            concluidas = []
            
            for atribuicao in atribuicoes:
                if atribuicao.concluida:
                    concluidas.append(atribuicao)
                else:
                    pendentes.append(atribuicao)
            
            return pendentes, concluidas
            
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar atribuições do revisor: {e}")
            raise
    
    @staticmethod
    def get_voting_statistics(voting_event_id: int) -> Dict:
        """Retorna estatísticas da votação."""
        try:
            voting_event = VotingEvent.query.get(voting_event_id)
            if not voting_event:
                return {}
            
            total_votos = VotingVote.query.filter_by(voting_event_id=voting_event_id).count()
            total_trabalhos = VotingWork.query.filter_by(voting_event_id=voting_event_id, ativo=True).count()
            total_categorias = VotingCategory.query.filter_by(voting_event_id=voting_event_id, ativa=True).count()
            total_atribuicoes = VotingAssignment.query.filter_by(voting_event_id=voting_event_id).count()
            atribuicoes_concluidas = VotingAssignment.query.filter_by(
                voting_event_id=voting_event_id, 
                concluida=True
            ).count()
            
            return {
                'total_votos': total_votos,
                'total_trabalhos': total_trabalhos,
                'total_categorias': total_categorias,
                'total_atribuicoes': total_atribuicoes,
                'atribuicoes_concluidas': atribuicoes_concluidas,
                'percentual_conclusao': (atribuicoes_concluidas / total_atribuicoes * 100) if total_atribuicoes > 0 else 0
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            return {}
    
    @staticmethod
    def _log_audit(voting_event_id: int, usuario_id: int = None, acao: str = '', 
                   detalhes: Dict = None, ip_address: str = None, user_agent: str = None):
        """Registra log de auditoria."""
        try:
            audit_log = VotingAuditLog(
                voting_event_id=voting_event_id,
                usuario_id=usuario_id,
                acao=acao,
                detalhes=detalhes or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(audit_log)
            db.session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao registrar log de auditoria: {e}")


class VotingWorkService:
    """Serviço específico para gerenciar trabalhos na votação."""
    
    @staticmethod
    def add_work_to_voting(voting_event_id: int, submission_id: int, **kwargs) -> VotingWork:
        """Adiciona um trabalho específico à votação."""
        try:
            submission = Submission.query.get(submission_id)
            if not submission:
                raise ValueError("Trabalho não encontrado")
            
            # Verificar se já está na votação
            existing_work = VotingWork.query.filter_by(
                voting_event_id=voting_event_id,
                submission_id=submission_id
            ).first()
            
            if existing_work:
                raise ValueError("Trabalho já está na votação")
            
            work = VotingWork(
                voting_event_id=voting_event_id,
                submission_id=submission_id,
                titulo=submission.title,
                resumo=submission.abstract,
                autores=kwargs.get('autores', ''),
                categoria_original=kwargs.get('categoria_original', ''),
                ordem_exibicao=kwargs.get('ordem_exibicao', 0)
            )
            
            db.session.add(work)
            db.session.commit()
            
            return work
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao adicionar trabalho à votação: {e}")
            raise


class VotingCategoryService:
    """Serviço específico para gerenciar categorias de votação."""
    
    @staticmethod
    def create_category(voting_event_id: int, **kwargs) -> VotingCategory:
        """Cria uma nova categoria de votação."""
        try:
            category = VotingCategory(
                voting_event_id=voting_event_id,
                nome=kwargs.get('nome'),
                descricao=kwargs.get('descricao', ''),
                ordem=kwargs.get('ordem', 0),
                pontuacao_minima=kwargs.get('pontuacao_minima', 0.0),
                pontuacao_maxima=kwargs.get('pontuacao_maxima', 10.0),
                tipo_pontuacao=kwargs.get('tipo_pontuacao', 'numerica')
            )
            
            db.session.add(category)
            db.session.commit()
            
            return category
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao criar categoria: {e}")
            raise
    
    @staticmethod
    def add_question_to_category(category_id: int, **kwargs) -> VotingQuestion:
        """Adiciona uma pergunta a uma categoria."""
        try:
            question = VotingQuestion(
                category_id=category_id,
                texto_pergunta=kwargs.get('texto_pergunta'),
                observacao_explicativa=kwargs.get('observacao_explicativa', ''),
                ordem=kwargs.get('ordem', 0),
                obrigatoria=kwargs.get('obrigatoria', True),
                tipo_resposta=kwargs.get('tipo_resposta', 'numerica'),
                opcoes_resposta=kwargs.get('opcoes_resposta'),
                valor_minimo=kwargs.get('valor_minimo'),
                valor_maximo=kwargs.get('valor_maximo'),
                casas_decimais=kwargs.get('casas_decimais', 1)
            )
            
            db.session.add(question)
            db.session.commit()
            
            return question
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao adicionar pergunta: {e}")
            raise

