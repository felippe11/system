import random
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from extensions import db
from models.submission_system import (
    ReviewerProfile,
    ReviewerPreference,
    DistributionConfig,
    AutoDistributionLog,
    SubmissionCategory,
)
from models.review import Submission, Assignment
from models.user import Usuario

logger = logging.getLogger(__name__)


class DistributionService:
    """Serviço para distribuição automática de trabalhos para revisores."""
    
    def __init__(self, evento_id: int):
        self.evento_id = evento_id
        self.config = self._load_config()
        self.log_entry = None
    
    def _load_config(self) -> DistributionConfig:
        """Carrega a configuração de distribuição do evento."""
        config = DistributionConfig.query.filter_by(evento_id=self.evento_id).first()
        if not config:
            # Criar configuração padrão
            config = DistributionConfig(
                evento_id=self.evento_id,
                reviewers_per_submission=2,
                distribution_mode="balanced",
                blind_type="single"
            )
            db.session.add(config)
            db.session.commit()
        return config
    
    def distribute_submissions(self, submission_ids: List[int] = None, seed: str = None) -> Dict:
        """Distribui submissões para revisores automaticamente."""
        try:
            # Inicializar log
            self.log_entry = AutoDistributionLog(
                evento_id=self.evento_id,
                distribution_seed=seed or str(random.randint(1000, 9999))
            )
            db.session.add(self.log_entry)
            db.session.flush()
            
            # Configurar seed para reproduzibilidade
            if seed:
                random.seed(seed)
            
            # Carregar dados
            submissions = self._load_submissions(submission_ids)
            reviewers = self._load_available_reviewers()
            
            if not submissions:
                raise ValueError("Nenhuma submissão encontrada para distribuição")
            
            if not reviewers:
                raise ValueError("Nenhum revisor disponível para distribuição")
            
            # Atualizar estatísticas do log
            self.log_entry.total_submissions = len(submissions)
            
            # Executar distribuição baseada no modo configurado
            assignments = self._execute_distribution(submissions, reviewers)
            
            # Salvar atribuições
            self._save_assignments(assignments)
            
            # Finalizar log
            self.log_entry.total_assignments = len(assignments)
            self.log_entry.mark_completed()
            db.session.commit()
            
            return {
                "success": True,
                "total_submissions": len(submissions),
                "total_assignments": len(assignments),
                "distribution_log_id": self.log_entry.id,
                "conflicts_detected": self.log_entry.conflicts_detected,
                "fallback_assignments": self.log_entry.fallback_assignments
            }
            
        except Exception as e:
            logger.error(f"Erro na distribuição: {str(e)}")
            if self.log_entry:
                self.log_entry.error_log.append({
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                self.log_entry.mark_completed()
                db.session.commit()
            raise
    
    def _load_submissions(self, submission_ids: List[int] = None) -> List[Submission]:
        """Carrega submissões para distribuição."""
        query = Submission.query.filter_by(evento_id=self.evento_id)
        
        if submission_ids:
            query = query.filter(Submission.id.in_(submission_ids))
        else:
            # Apenas submissões sem atribuições ou com atribuições incompletas
            query = query.outerjoin(Assignment).filter(
                (Assignment.id.is_(None)) | 
                (Assignment.completed == False)
            )
        
        return query.all()
    
    def _load_available_reviewers(self) -> List[ReviewerProfile]:
        """Carrega revisores disponíveis para o evento."""
        return ReviewerProfile.query.filter_by(
            evento_id=self.evento_id,
            available=True
        ).filter(
            ReviewerProfile.current_load < ReviewerProfile.max_assignments
        ).all()
    
    def _execute_distribution(self, submissions: List[Submission], reviewers: List[ReviewerProfile]) -> List[Dict]:
        """Executa a distribuição baseada no modo configurado."""
        if self.config.distribution_mode == "stratified":
            return self._stratified_distribution(submissions, reviewers)
        elif self.config.distribution_mode == "balanced":
            return self._balanced_distribution(submissions, reviewers)
        else:  # random
            return self._random_distribution(submissions, reviewers)
    
    def _balanced_distribution(self, submissions: List[Submission], reviewers: List[ReviewerProfile]) -> List[Dict]:
        """Distribuição balanceada considerando carga e afinidade."""
        assignments = []
        
        for submission in submissions:
            # Encontrar categoria da submissão
            category = self._get_submission_category(submission)
            
            # Calcular scores para cada revisor
            reviewer_scores = []
            for reviewer in reviewers:
                if not reviewer.can_accept_assignment:
                    continue
                
                score = self._calculate_reviewer_score(submission, reviewer, category)
                if score > 0:  # Apenas revisores elegíveis
                    reviewer_scores.append((reviewer, score))
            
            # Ordenar por score (maior primeiro)
            reviewer_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Atribuir aos melhores revisores disponíveis
            assigned_count = 0
            for reviewer, score in reviewer_scores:
                if assigned_count >= self.config.reviewers_per_submission:
                    break
                
                # Verificar conflitos
                if self._has_conflict(submission, reviewer):
                    self.log_entry.conflicts_detected += 1
                    continue
                
                assignments.append({
                    "submission_id": submission.id,
                    "reviewer_id": reviewer.usuario_id,
                    "score": score,
                    "assignment_type": "balanced"
                })
                
                # Atualizar carga do revisor
                reviewer.current_load += 1
                assigned_count += 1
            
            # Se não conseguiu atribuir o número necessário, usar fallback
            if assigned_count < self.config.reviewers_per_submission and self.config.fallback_to_random:
                self._fallback_assignment(submission, reviewers, assignments, assigned_count)
        
        return assignments
    
    def _stratified_distribution(self, submissions: List[Submission], reviewers: List[ReviewerProfile]) -> List[Dict]:
        """Distribuição estratificada por categoria."""
        assignments = []
        
        # Agrupar submissões por categoria
        submissions_by_category = defaultdict(list)
        for submission in submissions:
            category = self._get_submission_category(submission)
            submissions_by_category[category].append(submission)
        
        # Agrupar revisores por preferência de categoria
        reviewers_by_category = defaultdict(list)
        for reviewer in reviewers:
            for preference in reviewer.preferences:
                if preference.affinity_level >= self.config.min_affinity_level:
                    reviewers_by_category[preference.category.normalized_name].append(
                        (reviewer, preference.affinity_level)
                    )
        
        # Distribuir por categoria
        for category, category_submissions in submissions_by_category.items():
            category_reviewers = reviewers_by_category.get(category, [])
            
            if not category_reviewers and self.config.fallback_to_random:
                # Usar todos os revisores disponíveis como fallback
                category_reviewers = [(r, 1) for r in reviewers if r.can_accept_assignment]
            
            # Distribuir submissões da categoria
            for submission in category_submissions:
                assigned_count = 0
                
                # Ordenar revisores por afinidade
                sorted_reviewers = sorted(category_reviewers, key=lambda x: x[1], reverse=True)
                
                for reviewer, affinity in sorted_reviewers:
                    if assigned_count >= self.config.reviewers_per_submission:
                        break
                    
                    if not reviewer.can_accept_assignment:
                        continue
                    
                    if self._has_conflict(submission, reviewer):
                        self.log_entry.conflicts_detected += 1
                        continue
                    
                    assignments.append({
                        "submission_id": submission.id,
                        "reviewer_id": reviewer.usuario_id,
                        "score": affinity,
                        "assignment_type": "stratified"
                    })
                    
                    reviewer.current_load += 1
                    assigned_count += 1
        
        return assignments
    
    def _random_distribution(self, submissions: List[Submission], reviewers: List[ReviewerProfile]) -> List[Dict]:
        """Distribuição aleatória simples."""
        assignments = []
        
        for submission in submissions:
            available_reviewers = [r for r in reviewers if r.can_accept_assignment]
            random.shuffle(available_reviewers)
            
            assigned_count = 0
            for reviewer in available_reviewers:
                if assigned_count >= self.config.reviewers_per_submission:
                    break
                
                if self._has_conflict(submission, reviewer):
                    self.log_entry.conflicts_detected += 1
                    continue
                
                assignments.append({
                    "submission_id": submission.id,
                    "reviewer_id": reviewer.usuario_id,
                    "score": 1.0,
                    "assignment_type": "random"
                })
                
                reviewer.current_load += 1
                assigned_count += 1
        
        return assignments
    
    def _calculate_reviewer_score(self, submission: Submission, reviewer: ReviewerProfile, category: str) -> float:
        """Calcula score de adequação do revisor para a submissão."""
        score = 0.0
        
        # Score base por disponibilidade
        availability_score = reviewer.availability_percentage / 100
        score += availability_score * 0.3
        
        # Score por afinidade com a categoria
        affinity_score = 0.0
        for preference in reviewer.preferences:
            if preference.category.normalized_name == category:
                affinity_score = preference.affinity_level / 3.0  # Normalizar para 0-1
                break
        score += affinity_score * 0.7
        
        # Penalizar revisores sobrecarregados
        load_penalty = reviewer.current_load / reviewer.max_assignments
        score *= (1 - load_penalty * 0.5)
        
        return max(0.0, score)
    
    def _get_submission_category(self, submission: Submission) -> str:
        """Obtém a categoria normalizada da submissão."""
        # Tentar obter da categoria mapeada
        if hasattr(submission, 'attributes') and submission.attributes:
            category = submission.attributes.get('category', '')
            if category:
                return self._normalize_category(category)
        
        # Fallback para categoria padrão
        return "geral"
    
    def _normalize_category(self, category: str) -> str:
        """Normaliza nome da categoria."""
        # Implementar regras de normalização
        normalized = category.lower().strip()
        
        # Mapeamentos comuns
        mappings = {
            "matematica": "matemática",
            "mat": "matemática",
            "portugues": "português",
            "port": "português",
            "ciencias": "ciências",
            "hist": "história"
        }
        
        return mappings.get(normalized, normalized)
    
    def _has_conflict(self, submission: Submission, reviewer: ReviewerProfile) -> bool:
        """Verifica se há conflito de interesse."""
        if not self.config.enable_conflict_detection:
            return False
        
        # Conflito por autor (mesmo usuário)
        if submission.author_id == reviewer.usuario_id:
            return True
        
        # Conflito por instituição
        if reviewer.institution and hasattr(submission, 'attributes'):
            submission_institution = submission.attributes.get('institution', '')
            if submission_institution and submission_institution.lower() == reviewer.institution.lower():
                return True
        
        # Conflitos explícitos configurados
        if submission.author_id in reviewer.excluded_authors:
            return True
        
        return False
    
    def _fallback_assignment(self, submission: Submission, reviewers: List[ReviewerProfile], 
                           assignments: List[Dict], current_assigned: int):
        """Atribuição de fallback quando não há revisores suficientes."""
        needed = self.config.reviewers_per_submission - current_assigned
        
        # Tentar revisores com menor carga, mesmo que não tenham afinidade
        available_reviewers = [
            r for r in reviewers 
            if r.can_accept_assignment and not self._has_conflict(submission, r)
        ]
        
        # Ordenar por carga atual (menor primeiro)
        available_reviewers.sort(key=lambda x: x.current_load)
        
        for i in range(min(needed, len(available_reviewers))):
            reviewer = available_reviewers[i]
            
            assignments.append({
                "submission_id": submission.id,
                "reviewer_id": reviewer.usuario_id,
                "score": 0.1,  # Score baixo para indicar fallback
                "assignment_type": "fallback"
            })
            
            reviewer.current_load += 1
            self.log_entry.fallback_assignments += 1
    
    def _save_assignments(self, assignments: List[Dict]):
        """Salva as atribuições no banco de dados."""
        for assignment_data in assignments:
            # Verificar se já existe atribuição
            existing = Assignment.query.filter_by(
                submission_id=assignment_data["submission_id"],
                reviewer_id=assignment_data["reviewer_id"]
            ).first()
            
            if not existing:
                assignment = Assignment(
                    submission_id=assignment_data["submission_id"],
                    reviewer_id=assignment_data["reviewer_id"],
                    deadline=None  # Será definido pela configuração do evento
                )
                db.session.add(assignment)
    
    def get_distribution_stats(self) -> Dict:
        """Retorna estatísticas da distribuição atual."""
        # Estatísticas de submissões
        total_submissions = Submission.query.filter_by(evento_id=self.evento_id).count()
        assigned_submissions = db.session.query(Submission.id).join(Assignment).filter(
            Submission.evento_id == self.evento_id
        ).distinct().count()
        
        # Estatísticas de revisores
        total_reviewers = ReviewerProfile.query.filter_by(evento_id=self.evento_id).count()
        active_reviewers = ReviewerProfile.query.filter_by(
            evento_id=self.evento_id, available=True
        ).count()
        
        # Carga de trabalho
        reviewer_loads = db.session.query(
            ReviewerProfile.current_load,
            ReviewerProfile.max_assignments
        ).filter_by(evento_id=self.evento_id).all()
        
        avg_load = sum(load for load, _ in reviewer_loads) / len(reviewer_loads) if reviewer_loads else 0
        avg_capacity = sum(capacity for _, capacity in reviewer_loads) / len(reviewer_loads) if reviewer_loads else 0
        
        return {
            "total_submissions": total_submissions,
            "assigned_submissions": assigned_submissions,
            "pending_submissions": total_submissions - assigned_submissions,
            "total_reviewers": total_reviewers,
            "active_reviewers": active_reviewers,
            "average_load": round(avg_load, 2),
            "average_capacity": round(avg_capacity, 2),
            "utilization_rate": round((avg_load / avg_capacity * 100) if avg_capacity > 0 else 0, 2)
        }
    
    def rebalance_assignments(self) -> Dict:
        """Rebalanceia atribuições existentes para melhor distribuição."""
        # Implementar lógica de rebalanceamento
        # Por enquanto, retorna estatísticas atuais
        return self.get_distribution_stats()