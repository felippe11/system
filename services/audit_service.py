import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import func, desc, and_, or_
from io import BytesIO
import csv
import json

from extensions import db
from models.submission_system import (
    AutoDistributionLog,
    ReviewerProfile,
    DistributionConfig,
    ImportedSubmission,
    SpreadsheetMapping,
)
from models.review import Assignment, Submission, Review
from models.user import Usuario
from models.event import Evento

logger = logging.getLogger(__name__)


class AuditService:
    """Serviço para auditoria e relatórios do sistema de distribuição."""
    
    def __init__(self, evento_id: int):
        self.evento_id = evento_id
        self.evento = Evento.query.get(evento_id)
    
    def generate_distribution_report(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Gera relatório completo de distribuições."""
        try:
            # Filtros de data
            query = AutoDistributionLog.query.filter_by(evento_id=self.evento_id)
            
            if start_date:
                query = query.filter(AutoDistributionLog.started_at >= start_date)
            if end_date:
                query = query.filter(AutoDistributionLog.started_at <= end_date)
            
            distributions = query.order_by(desc(AutoDistributionLog.started_at)).all()
            
            # Estatísticas gerais
            total_distributions = len(distributions)
            total_submissions_distributed = sum(d.total_submissions for d in distributions)
            total_assignments_created = sum(d.total_assignments for d in distributions)
            total_conflicts_detected = sum(d.conflicts_detected for d in distributions)
            
            # Análise por período
            period_analysis = self._analyze_distribution_periods(distributions)
            
            # Análise de eficiência
            efficiency_metrics = self._calculate_efficiency_metrics(distributions)
            
            # Análise de revisores
            reviewer_analysis = self._analyze_reviewer_workload()
            
            return {
                "success": True,
                "report_generated_at": datetime.now().isoformat(),
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "summary": {
                    "total_distributions": total_distributions,
                    "total_submissions_distributed": total_submissions_distributed,
                    "total_assignments_created": total_assignments_created,
                    "total_conflicts_detected": total_conflicts_detected,
                    "average_assignments_per_distribution": round(total_assignments_created / max(total_distributions, 1), 2)
                },
                "distributions": [{
                    "id": d.id,
                    "started_at": d.started_at.isoformat(),
                    "completed_at": d.completed_at.isoformat() if d.completed_at else None,
                    "mode": d.mode,
                    "total_submissions": d.total_submissions,
                    "total_assignments": d.total_assignments,
                    "conflicts_detected": d.conflicts_detected,
                    "fallback_assignments": d.fallback_assignments,
                    "success_rate": self._calculate_distribution_success_rate(d),
                    "duration_minutes": self._calculate_duration_minutes(d)
                } for d in distributions],
                "period_analysis": period_analysis,
                "efficiency_metrics": efficiency_metrics,
                "reviewer_analysis": reviewer_analysis
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de distribuição: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def generate_reviewer_performance_report(self) -> Dict:
        """Gera relatório de desempenho dos revisores."""
        try:
            # Buscar todos os revisores com atribuições
            reviewers_query = db.session.query(
                Usuario.id,
                Usuario.nome,
                Usuario.email,
                func.count(Assignment.id).label('total_assignments'),
                func.count(Review.id).label('completed_reviews'),
                func.avg(Review.nota_final).label('average_score')
            ).join(
                Assignment, Usuario.id == Assignment.reviewer_id
            ).join(
                Submission, Assignment.submission_id == Submission.id
            ).outerjoin(
                Review, Assignment.id == Review.assignment_id
            ).filter(
                Submission.evento_id == self.evento_id
            ).group_by(
                Usuario.id, Usuario.nome, Usuario.email
            ).all()
            
            reviewer_performance = []
            for reviewer in reviewers_query:
                # Calcular métricas adicionais
                completion_rate = (reviewer.completed_reviews / max(reviewer.total_assignments, 1)) * 100
                
                # Buscar atribuições em atraso
                overdue_assignments = Assignment.query.join(Submission).filter(
                    Assignment.reviewer_id == reviewer.id,
                    Submission.evento_id == self.evento_id,
                    Assignment.completed == False,
                    Assignment.deadline < datetime.now()
                ).count()
                
                # Buscar tempo médio de revisão
                avg_review_time = self._calculate_average_review_time(reviewer.id)
                
                reviewer_performance.append({
                    "reviewer_id": reviewer.id,
                    "name": reviewer.nome,
                    "email": reviewer.email,
                    "total_assignments": reviewer.total_assignments,
                    "completed_reviews": reviewer.completed_reviews,
                    "completion_rate": round(completion_rate, 2),
                    "average_score": round(reviewer.average_score or 0, 2),
                    "overdue_assignments": overdue_assignments,
                    "average_review_time_days": avg_review_time
                })
            
            # Estatísticas gerais
            total_reviewers = len(reviewer_performance)
            avg_completion_rate = sum(r['completion_rate'] for r in reviewer_performance) / max(total_reviewers, 1)
            
            return {
                "success": True,
                "report_generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_reviewers": total_reviewers,
                    "average_completion_rate": round(avg_completion_rate, 2),
                    "total_assignments": sum(r['total_assignments'] for r in reviewer_performance),
                    "total_completed_reviews": sum(r['completed_reviews'] for r in reviewer_performance)
                },
                "reviewers": reviewer_performance
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de desempenho: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def generate_import_audit_report(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Gera relatório de auditoria de importações."""
        try:
            # Buscar importações
            query = ImportedSubmission.query.filter_by(evento_id=self.evento_id)
            
            if start_date:
                query = query.filter(ImportedSubmission.imported_at >= start_date)
            if end_date:
                query = query.filter(ImportedSubmission.imported_at <= end_date)
            
            imports = query.all()
            
            # Agrupar por batch_id
            batches = {}
            for imp in imports:
                batch_id = imp.batch_id
                if batch_id not in batches:
                    batches[batch_id] = {
                        "batch_id": batch_id,
                        "imported_at": imp.imported_at,
                        "total_records": 0,
                        "processed_records": 0,
                        "error_records": 0,
                        "errors": []
                    }
                
                batches[batch_id]["total_records"] += 1
                
                if imp.processed:
                    batches[batch_id]["processed_records"] += 1
                
                if imp.error_message:
                    batches[batch_id]["error_records"] += 1
                    batches[batch_id]["errors"].append({
                        "row": imp.row_number,
                        "error": imp.error_message
                    })
            
            # Converter para lista e calcular métricas
            batch_list = []
            for batch in batches.values():
                batch["success_rate"] = round(
                    (batch["processed_records"] / max(batch["total_records"], 1)) * 100, 2
                )
                batch["imported_at"] = batch["imported_at"].isoformat()
                batch_list.append(batch)
            
            # Ordenar por data
            batch_list.sort(key=lambda x: x["imported_at"], reverse=True)
            
            # Estatísticas gerais
            total_batches = len(batch_list)
            total_records = sum(b["total_records"] for b in batch_list)
            total_processed = sum(b["processed_records"] for b in batch_list)
            total_errors = sum(b["error_records"] for b in batch_list)
            
            return {
                "success": True,
                "report_generated_at": datetime.now().isoformat(),
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "summary": {
                    "total_batches": total_batches,
                    "total_records": total_records,
                    "total_processed": total_processed,
                    "total_errors": total_errors,
                    "overall_success_rate": round((total_processed / max(total_records, 1)) * 100, 2)
                },
                "batches": batch_list
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de importação: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def generate_conflict_analysis_report(self) -> Dict:
        """Gera relatório de análise de conflitos."""
        try:
            # Buscar logs de distribuição com conflitos
            distributions = AutoDistributionLog.query.filter(
                AutoDistributionLog.evento_id == self.evento_id,
                AutoDistributionLog.conflicts_detected > 0
            ).all()
            
            conflict_analysis = []
            total_conflicts = 0
            
            for dist in distributions:
                # Analisar detalhes dos conflitos (se disponível nos logs)
                conflict_details = self._extract_conflict_details(dist)
                
                conflict_analysis.append({
                    "distribution_id": dist.id,
                    "date": dist.started_at.isoformat(),
                    "conflicts_detected": dist.conflicts_detected,
                    "total_submissions": dist.total_submissions,
                    "conflict_rate": round((dist.conflicts_detected / max(dist.total_submissions, 1)) * 100, 2),
                    "details": conflict_details
                })
                
                total_conflicts += dist.conflicts_detected
            
            # Análise de padrões de conflito
            conflict_patterns = self._analyze_conflict_patterns()
            
            return {
                "success": True,
                "report_generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_distributions_with_conflicts": len(conflict_analysis),
                    "total_conflicts_detected": total_conflicts,
                    "average_conflicts_per_distribution": round(total_conflicts / max(len(distributions), 1), 2)
                },
                "distributions": conflict_analysis,
                "conflict_patterns": conflict_patterns
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de conflitos: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def export_audit_data_csv(self, report_type: str, **kwargs) -> BytesIO:
        """Exporta dados de auditoria em formato CSV."""
        try:
            output = BytesIO()
            
            if report_type == "distribution":
                data = self.generate_distribution_report(**kwargs)
                self._write_distribution_csv(output, data)
            elif report_type == "reviewer_performance":
                data = self.generate_reviewer_performance_report()
                self._write_reviewer_performance_csv(output, data)
            elif report_type == "import_audit":
                data = self.generate_import_audit_report(**kwargs)
                self._write_import_audit_csv(output, data)
            else:
                raise ValueError(f"Tipo de relatório não suportado: {report_type}")
            
            output.seek(0)
            return output
            
        except Exception as e:
            logger.error(f"Erro ao exportar CSV: {str(e)}")
            raise
    
    def _analyze_distribution_periods(
        self, distributions: List[AutoDistributionLog]
    ) -> Dict:
        """Analisa distribuições por período."""
        if not distributions:
            return {}
        
        # Agrupar por mês
        monthly_stats = {}
        for dist in distributions:
            month_key = dist.started_at.strftime("%Y-%m")
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    "month": month_key,
                    "distributions": 0,
                    "submissions": 0,
                    "assignments": 0,
                    "conflicts": 0
                }
            
            monthly_stats[month_key]["distributions"] += 1
            monthly_stats[month_key]["submissions"] += dist.total_submissions
            monthly_stats[month_key]["assignments"] += dist.total_assignments
            monthly_stats[month_key]["conflicts"] += dist.conflicts_detected
        
        return {
            "monthly_breakdown": list(monthly_stats.values()),
            "peak_month": max(monthly_stats.values(), key=lambda x: x["submissions"])["month"] if monthly_stats else None
        }
    
    def _calculate_efficiency_metrics(
        self, distributions: List[AutoDistributionLog]
    ) -> Dict:
        """Calcula métricas de eficiência."""
        if not distributions:
            return {}
        
        # Tempo médio de distribuição
        completed_distributions = [d for d in distributions if d.completed_at]
        avg_duration = 0
        
        if completed_distributions:
            total_duration = sum(
                (d.completed_at - d.started_at).total_seconds() / 60
                for d in completed_distributions
            )
            avg_duration = total_duration / len(completed_distributions)
        
        # Taxa de sucesso média
        success_rates = [self._calculate_distribution_success_rate(d) for d in distributions]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
        
        return {
            "average_duration_minutes": round(avg_duration, 2),
            "average_success_rate": round(avg_success_rate, 2),
            "total_completed_distributions": len(completed_distributions),
            "completion_rate": round((len(completed_distributions) / len(distributions)) * 100, 2)
        }
    
    def _analyze_reviewer_workload(self) -> Dict:
        """Analisa carga de trabalho dos revisores."""
        try:
            # Distribuição de carga de trabalho
            workload_query = db.session.query(
                Usuario.id,
                Usuario.nome,
                func.count(Assignment.id).label('assignment_count')
            ).join(
                Assignment, Usuario.id == Assignment.reviewer_id
            ).join(
                Submission, Assignment.submission_id == Submission.id
            ).filter(
                Submission.evento_id == self.evento_id
            ).group_by(
                Usuario.id, Usuario.nome
            ).all()
            
            workloads = [r.assignment_count for r in workload_query]
            
            if workloads:
                return {
                    "total_reviewers": len(workloads),
                    "min_assignments": min(workloads),
                    "max_assignments": max(workloads),
                    "avg_assignments": round(sum(workloads) / len(workloads), 2),
                    "workload_distribution": {
                        "0-5": len([w for w in workloads if 0 <= w <= 5]),
                        "6-10": len([w for w in workloads if 6 <= w <= 10]),
                        "11-15": len([w for w in workloads if 11 <= w <= 15]),
                        "16+": len([w for w in workloads if w > 15])
                    }
                }
            
            return {"total_reviewers": 0}
            
        except Exception as e:
            logger.error(f"Erro ao analisar carga de trabalho: {str(e)}")
            return {}
    
    def _calculate_distribution_success_rate(
        self, distribution: AutoDistributionLog
    ) -> float:
        """Calcula taxa de sucesso de uma distribuição."""
        if distribution.total_submissions == 0:
            return 0.0
        
        successful_assignments = distribution.total_assignments - distribution.fallback_assignments
        return round((successful_assignments / distribution.total_submissions) * 100, 2)
    
    def _calculate_duration_minutes(
        self, distribution: AutoDistributionLog
    ) -> Optional[float]:
        """Calcula duração da distribuição em minutos."""
        if not distribution.completed_at:
            return None
        
        duration = distribution.completed_at - distribution.started_at
        return round(duration.total_seconds() / 60, 2)
    
    def _calculate_average_review_time(self, reviewer_id: int) -> Optional[float]:
        """Calcula tempo médio de revisão para um revisor."""
        try:
            completed_reviews = db.session.query(
                Assignment.created_at,
                Review.created_at
            ).join(
                Review, Assignment.id == Review.assignment_id
            ).join(
                Submission, Assignment.submission_id == Submission.id
            ).filter(
                Assignment.reviewer_id == reviewer_id,
                Submission.evento_id == self.evento_id,
                Review.created_at.isnot(None)
            ).all()
            
            if completed_reviews:
                total_days = sum(
                    (review.created_at - assignment.created_at).days
                    for assignment, review in completed_reviews
                )
                return round(total_days / len(completed_reviews), 2)
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao calcular tempo médio de revisão: {str(e)}")
            return None
    
    def _extract_conflict_details(
        self, distribution: AutoDistributionLog
    ) -> List[Dict]:
        """Extrai detalhes dos conflitos de uma distribuição."""
        # Por enquanto, retorna informações básicas
        # TODO: Implementar log detalhado de conflitos
        return [{
            "type": "general",
            "count": distribution.conflicts_detected,
            "description": "Conflitos detectados durante a distribuição"
        }]
    
    def _analyze_conflict_patterns(self) -> Dict:
        """Analisa padrões de conflitos."""
        # TODO: Implementar análise detalhada de padrões
        return {
            "most_common_conflict_type": "author_institution",
            "conflict_frequency_by_category": {},
            "recommendations": [
                "Revisar configurações de conflito de interesse",
                "Considerar expandir pool de revisores"
            ]
        }
    
    def _write_distribution_csv(self, output: BytesIO, data: Dict):
        """Escreve dados de distribuição em CSV."""
        if not data.get("success"):
            return
        
        writer = csv.writer(output, delimiter=';')
        
        # Cabeçalho
        writer.writerow([
            'ID', 'Data Início', 'Data Conclusão', 'Modo', 'Submissões',
            'Atribuições', 'Conflitos', 'Fallbacks', 'Taxa Sucesso (%)', 'Duração (min)'
        ])
        
        # Dados
        for dist in data.get("distributions", []):
            writer.writerow([
                dist['id'],
                dist['started_at'],
                dist['completed_at'] or '',
                dist['mode'],
                dist['total_submissions'],
                dist['total_assignments'],
                dist['conflicts_detected'],
                dist['fallback_assignments'],
                dist['success_rate'],
                dist['duration_minutes'] or ''
            ])
    
    def _write_reviewer_performance_csv(self, output: BytesIO, data: Dict):
        """Escreve dados de desempenho em CSV."""
        if not data.get("success"):
            return
        
        writer = csv.writer(output, delimiter=';')
        
        # Cabeçalho
        writer.writerow([
            'ID', 'Nome', 'Email', 'Total Atribuições', 'Revisões Concluídas',
            'Taxa Conclusão (%)', 'Nota Média', 'Atribuições em Atraso', 'Tempo Médio (dias)'
        ])
        
        # Dados
        for reviewer in data.get("reviewers", []):
            writer.writerow([
                reviewer['reviewer_id'],
                reviewer['name'],
                reviewer['email'],
                reviewer['total_assignments'],
                reviewer['completed_reviews'],
                reviewer['completion_rate'],
                reviewer['average_score'],
                reviewer['overdue_assignments'],
                reviewer['average_review_time_days'] or ''
            ])
    
    def _write_import_audit_csv(self, output: BytesIO, data: Dict):
        """Escreve dados de auditoria de importação em CSV."""
        if not data.get("success"):
            return
        
        writer = csv.writer(output, delimiter=';')
        
        # Cabeçalho
        writer.writerow([
            'Lote', 'Data Importação', 'Total Registros', 'Processados',
            'Com Erros', 'Taxa Sucesso (%)'
        ])
        
        # Dados
        for batch in data.get("batches", []):
            writer.writerow([
                batch['batch_id'],
                batch['imported_at'],
                batch['total_records'],
                batch['processed_records'],
                batch['error_records'],
                batch['success_rate']
            ])