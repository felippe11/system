from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import and_, or_, func
from extensions import db
from models.review import Submission, Review, Assignment
from models import Usuario, Evento
from models.review import RevisaoConfig
import logging

logger = logging.getLogger(__name__)


class SubmissionService:
    """Serviço unificado para gerenciamento de submissões e atribuição de revisores."""
    
    @staticmethod
    def create_submission(title: str, author_id: Optional[int], evento_id: int,
                         file_path: str = None, content: str = None,
                         abstract: str = None, area_id: int = None,
                         attributes: Optional[dict] = None) -> Submission:
        """Cria uma nova submissão com validações."""

        # Permitir múltiplas submissões do mesmo usuário para o mesmo evento
        # Validação de submissão única removida para permitir flexibilidade

        # Validar se evento existe
        evento = Evento.query.get(evento_id)
        if not evento:
            raise ValueError("Evento não encontrado")

        resolved_author_id = author_id
        if resolved_author_id is not None:
            author = db.session.get(Usuario, resolved_author_id)
            if not author:
                logger.warning(
                    "Autor %s não encontrado na tabela de usuários; "
                    "continuando sem vínculo de autor.",
                    resolved_author_id,
                )
                resolved_author_id = None

        submission_attributes = attributes or {}

        # Validar tamanho do arquivo se fornecido
        if file_path:
            import os
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                max_size = 50 * 1024 * 1024  # 50MB
                if file_size > max_size:
                    raise ValueError("Arquivo muito grande (máximo 50MB)")
        
        # Gerar código de acesso e hash
        import secrets
        from werkzeug.security import generate_password_hash
        access_code = secrets.token_urlsafe(8)  # Código de 8 caracteres
        code_hash = generate_password_hash(access_code)
        
        submission = Submission(
            title=title,
            author_id=resolved_author_id,
            evento_id=evento_id,
            file_path=file_path,
            content=content,
            abstract=abstract,
            area_id=area_id,
            status='submitted',
            code_hash=code_hash,
            attributes=submission_attributes,
        )
        
        db.session.add(submission)
        db.session.flush()
        
        # Atribuir revisores automaticamente (temporariamente desabilitado)
        # try:
        #     SubmissionService.auto_assign_reviewers(submission.id)
        # except Exception as e:
        #     logger.warning(f"Erro na atribuição automática de revisores: {e}")
        
        db.session.commit()
        return submission
    
    @staticmethod
    def auto_assign_reviewers(submission_id: int) -> List[Assignment]:
        """Atribui revisores automaticamente para uma submissão."""
        
        submission = Submission.query.get(submission_id)
        if not submission:
            raise ValueError("Submissão não encontrada")
        
        # Obter configuração de revisão do evento
        config = RevisaoConfig.query.filter_by(evento_id=submission.evento_id).first()
        num_revisores = config.numero_revisores if config else 2
        prazo_dias = 14  # padrão
        
        if config and config.prazo_revisao:
            prazo_dias = (config.prazo_revisao - datetime.utcnow()).days
            if prazo_dias < 1:
                prazo_dias = 7  # mínimo de 7 dias
        
        # Encontrar revisores disponíveis
        revisores = SubmissionService._find_available_reviewers(
            submission.evento_id, 
            submission.area_id,
            submission.author_id,
            num_revisores
        )
        
        assignments = []
        for revisor in revisores[:num_revisores]:
            assignment = Assignment(
                resposta_formulario_id=submission_id,  # Corrigido: usar resposta_formulario_id
                reviewer_id=revisor.id,
                deadline=datetime.utcnow() + timedelta(days=prazo_dias)
            )
            db.session.add(assignment)
            assignments.append(assignment)
        
        return assignments
    
    @staticmethod
    def _find_available_reviewers(evento_id: int, area_id: Optional[int], 
                                 author_id: int, num_needed: int) -> List[Usuario]:
        """Encontra revisores disponíveis considerando carga de trabalho e especialidade."""
        
        # Query base para revisores
        query = db.session.query(Usuario).filter(
            Usuario.tipo.in_(['professor', 'ministrante', 'admin']),
            Usuario.ativo == True,
            Usuario.id != author_id  # Não pode revisar próprio trabalho
        )
        
        # Filtrar por evento se necessário
        if evento_id:
            query = query.filter(
                or_(
                    Usuario.evento_id == evento_id,
                    Usuario.tipo == 'admin'  # Admins podem revisar qualquer evento
                )
            )
        
        # Calcular carga de trabalho atual de cada revisor
        subquery = db.session.query(
            Assignment.reviewer_id,
            func.count(Assignment.id).label('current_load')
        ).filter(
            Assignment.completed == False  # Apenas revisões pendentes
        ).group_by(Assignment.reviewer_id).subquery()
        
        # Juntar com carga de trabalho e ordenar por menor carga
        query = query.outerjoin(
            subquery, Usuario.id == subquery.c.reviewer_id
        ).order_by(
            func.coalesce(subquery.c.current_load, 0),  # Menor carga primeiro
            func.random()  # Randomizar entre revisores com mesma carga
        )
        
        return query.limit(num_needed * 2).all()  # Buscar mais que necessário
    
    @staticmethod
    def get_submission_stats(evento_id: Optional[int] = None) -> dict:
        """Retorna estatísticas das submissões."""
        
        query = db.session.query(Submission)
        if evento_id:
            query = query.filter(Submission.evento_id == evento_id)
        
        total = query.count()
        pending = query.filter(Submission.status == 'submitted').count()
        under_review = query.filter(Submission.status == 'under_review').count()
        completed = query.filter(Submission.status.in_(['accepted', 'rejected'])).count()
        
        return {
            'total': total,
            'pending': pending,
            'under_review': under_review,
            'completed': completed
        }
    
    @staticmethod
    def update_submission_status(submission_id: int) -> None:
        """Atualiza o status da submissão baseado nas revisões."""
        
        submission = Submission.query.get(submission_id)
        if not submission:
            return
        
        # Contar revisões
        total_reviews = Review.query.filter_by(submission_id=submission_id).count()
        completed_reviews = Review.query.filter(
            Review.submission_id == submission_id,
            Review.finished_at.isnot(None)
        ).count()
        
        # Obter configuração do evento
        config = RevisaoConfig.query.filter_by(evento_id=submission.evento_id).first()
        required_reviews = config.numero_revisores if config else 2
        
        # Atualizar status
        if completed_reviews == 0:
            new_status = 'submitted'
        elif completed_reviews < required_reviews:
            new_status = 'under_review'
        else:
            # Verificar decisões dos revisores
            decisions = db.session.query(Review.decision).filter(
                Review.submission_id == submission_id,
                Review.finished_at.isnot(None),
                Review.decision.isnot(None)
            ).all()
            
            if not decisions:
                new_status = 'under_review'
            else:
                # Lógica de decisão: maioria simples
                accept_count = sum(1 for d in decisions if d[0] == 'accept')
                reject_count = sum(1 for d in decisions if d[0] == 'reject')
                
                if accept_count > reject_count:
                    new_status = 'accepted'
                elif reject_count > accept_count:
                    new_status = 'rejected'
                else:
                    new_status = 'under_review'  # Empate, aguardar mais revisões
        
        if submission.status != new_status:
            submission.status = new_status
            db.session.commit()
    
    @staticmethod
    def validate_file_upload(file, allowed_extensions: List[str], max_size_mb: int = 50) -> bool:
        """Valida arquivo de upload."""
        
        if not file or not file.filename:
            return False
        
        # Verificar extensão
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            raise ValueError(f"Tipo de arquivo não permitido. Permitidos: {', '.join(allowed_extensions)}")
        
        # Verificar tamanho (se possível)
        try:
            file.seek(0, 2)  # Ir para o final
            size = file.tell()
            file.seek(0)  # Voltar ao início
            
            if size > max_size_mb * 1024 * 1024:
                raise ValueError(f"Arquivo muito grande. Máximo: {max_size_mb}MB")
        except:
            pass  # Se não conseguir verificar tamanho, continuar
        
        return True
