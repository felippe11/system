import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from jinja2 import Template

from extensions import db
from models.submission_system import (
    ReviewerProfile,
    AutoDistributionLog,
    DistributionConfig,
)
from models.review import Assignment, Submission
from models.user import Usuario
from models.event import Evento
from services.email_service import send_email

logger = logging.getLogger(__name__)


class NotificationService:
    """Serviço para notificações automáticas do sistema de distribuição."""
    
    def __init__(self, evento_id: int):
        self.evento_id = evento_id
        self.evento = Evento.query.get(evento_id)
    
    def notify_distribution_completed(
        self, distribution_log: AutoDistributionLog
    ) -> Dict:
        """Notifica sobre conclusão da distribuição automática."""
        try:
            # Obter administradores do evento
            admins = self._get_event_admins()
            
            # Preparar dados do email
            template_data = {
                "evento_nome": self.evento.nome,
                "total_submissions": distribution_log.total_submissions,
                "total_assignments": distribution_log.total_assignments,
                "conflicts_detected": distribution_log.conflicts_detected,
                "fallback_assignments": distribution_log.fallback_assignments,
                "distribution_date": distribution_log.completed_at.strftime("%d/%m/%Y %H:%M"),
                "success_rate": self._calculate_success_rate(distribution_log)
            }
            
            # Template do email
            subject = f"Distribuição Automática Concluída - {self.evento.nome}"
            html_template = self._get_distribution_completed_template()
            html_content = html_template.render(**template_data)
            
            # Enviar para todos os administradores
            sent_count = 0
            for admin in admins:
                try:
                    send_email(
                        to=admin.email,
                        subject=subject,
                        html=html_content
                    )
                    sent_count += 1
                    logger.info(f"Notificação enviada para admin: {admin.email}")
                except Exception as e:
                    logger.error(f"Erro ao enviar notificação para {admin.email}: {str(e)}")
            
            return {
                "success": True,
                "notifications_sent": sent_count,
                "total_admins": len(admins)
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificações de distribuição: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def notify_reviewers_assignments(self, assignment_ids: List[int] = None) -> Dict:
        """Notifica revisores sobre novas atribuições."""
        try:
            # Obter atribuições
            query = Assignment.query.join(Submission).filter(
                Submission.evento_id == self.evento_id,
                Assignment.notified == False
            )
            
            if assignment_ids:
                query = query.filter(Assignment.id.in_(assignment_ids))
            
            assignments = query.all()
            
            # Agrupar por revisor
            assignments_by_reviewer = {}
            for assignment in assignments:
                reviewer_id = assignment.reviewer_id
                if reviewer_id not in assignments_by_reviewer:
                    assignments_by_reviewer[reviewer_id] = []
                assignments_by_reviewer[reviewer_id].append(assignment)
            
            # Enviar notificações
            sent_count = 0
            for reviewer_id, reviewer_assignments in assignments_by_reviewer.items():
                try:
                    reviewer = Usuario.query.get(reviewer_id)
                    if reviewer and reviewer.email:
                        self._send_reviewer_notification(reviewer, reviewer_assignments)
                        
                        # Marcar como notificado
                        for assignment in reviewer_assignments:
                            assignment.notified = True
                        
                        sent_count += 1
                        logger.info(f"Notificação enviada para revisor: {reviewer.email}")
                        
                except Exception as e:
                    logger.error(f"Erro ao notificar revisor {reviewer_id}: {str(e)}")
            
            db.session.commit()
            
            return {
                "success": True,
                "notifications_sent": sent_count,
                "total_assignments": len(assignments)
            }
            
        except Exception as e:
            logger.error(f"Erro ao notificar revisores: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def notify_deadline_reminders(self, days_before: int = 3) -> Dict:
        """Envia lembretes de prazo para revisores."""
        try:
            # Calcular data limite
            reminder_date = datetime.now() + timedelta(days=days_before)
            
            # Buscar atribuições próximas do prazo
            assignments = Assignment.query.join(Submission).filter(
                Submission.evento_id == self.evento_id,
                Assignment.completed == False,
                Assignment.deadline <= reminder_date,
                Assignment.deadline > datetime.now(),
                Assignment.reminder_sent == False
            ).all()
            
            sent_count = 0
            for assignment in assignments:
                try:
                    reviewer = Usuario.query.get(assignment.reviewer_id)
                    if reviewer and reviewer.email:
                        self._send_deadline_reminder(reviewer, assignment)
                        assignment.reminder_sent = True
                        sent_count += 1
                        logger.info(f"Lembrete enviado para: {reviewer.email}")
                        
                except Exception as e:
                    logger.error(f"Erro ao enviar lembrete para assignment {assignment.id}: {str(e)}")
            
            db.session.commit()
            
            return {
                "success": True,
                "reminders_sent": sent_count,
                "total_pending": len(assignments)
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar lembretes: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def notify_import_completed(self, batch_id: str, stats: Dict) -> Dict:
        """Notifica sobre conclusão da importação de planilhas."""
        try:
            admins = self._get_event_admins()
            
            template_data = {
                "evento_nome": self.evento.nome,
                "batch_id": batch_id,
                "total_imported": stats.get("total_imported", 0),
                "processed": stats.get("processed", 0),
                "with_errors": stats.get("with_errors", 0),
                "success_rate": stats.get("success_rate", 0),
                "import_date": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            
            subject = f"Importação de Submissões Concluída - {self.evento.nome}"
            html_template = self._get_import_completed_template()
            html_content = html_template.render(**template_data)
            
            sent_count = 0
            for admin in admins:
                try:
                    send_email(
                        to=admin.email,
                        subject=subject,
                        html=html_content
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Erro ao enviar notificação de importação para {admin.email}: {str(e)}")
            
            return {
                "success": True,
                "notifications_sent": sent_count
            }
            
        except Exception as e:
            logger.error(f"Erro ao notificar importação: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _get_event_admins(self) -> List[Usuario]:
        """Obtém administradores do evento."""
        # Por enquanto, retorna todos os admins
        # TODO: Implementar administradores específicos por evento
        return Usuario.query.filter_by(tipo='admin').all()
    
    def _send_reviewer_notification(self, reviewer: Usuario, assignments: List[Assignment]):
        """Envia notificação individual para revisor."""
        template_data = {
            "reviewer_name": reviewer.nome,
            "evento_nome": self.evento.nome,
            "assignments_count": len(assignments),
            "assignments": [{
                "title": assignment.submission.title,
                "deadline": assignment.deadline.strftime("%d/%m/%Y") if assignment.deadline else "A definir",
                "submission_id": assignment.submission.id
            } for assignment in assignments]
        }
        
        subject = f"Novas Atribuições de Revisão - {self.evento.nome}"
        html_template = self._get_reviewer_notification_template()
        html_content = html_template.render(**template_data)
        
        send_email(
            to=reviewer.email,
            subject=subject,
            html=html_content
        )
    
    def _send_deadline_reminder(self, reviewer: Usuario, assignment: Assignment):
        """Envia lembrete de prazo para revisor."""
        days_left = (assignment.deadline - datetime.now()).days if assignment.deadline else 0
        
        template_data = {
            "reviewer_name": reviewer.nome,
            "evento_nome": self.evento.nome,
            "submission_title": assignment.submission.title,
            "deadline": assignment.deadline.strftime("%d/%m/%Y %H:%M") if assignment.deadline else "A definir",
            "days_left": max(0, days_left),
            "submission_id": assignment.submission.id
        }
        
        subject = f"Lembrete: Prazo de Revisão - {self.evento.nome}"
        html_template = self._get_deadline_reminder_template()
        html_content = html_template.render(**template_data)
        
        send_email(
            to=reviewer.email,
            subject=subject,
            html=html_content
        )
    
    def _calculate_success_rate(
        self, distribution_log: AutoDistributionLog
    ) -> float:
        """Calcula taxa de sucesso da distribuição."""
        if distribution_log.total_submissions == 0:
            return 0.0
        
        successful_assignments = distribution_log.total_assignments - distribution_log.fallback_assignments
        return round((successful_assignments / distribution_log.total_submissions) * 100, 2)
    
    def _get_distribution_completed_template(self) -> Template:
        """Template para notificação de distribuição concluída."""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Distribuição Concluída</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">🎯 Distribuição Automática Concluída</h2>
                
                <p>A distribuição automática de submissões foi concluída para o evento <strong>{{ evento_nome }}</strong>.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">📊 Resumo da Distribuição</h3>
                    <ul style="list-style: none; padding: 0;">
                        <li>📝 <strong>Total de Submissões:</strong> {{ total_submissions }}</li>
                        <li>👥 <strong>Total de Atribuições:</strong> {{ total_assignments }}</li>
                        <li>⚠️ <strong>Conflitos Detectados:</strong> {{ conflicts_detected }}</li>
                        <li>🔄 <strong>Atribuições de Fallback:</strong> {{ fallback_assignments }}</li>
                        <li>✅ <strong>Taxa de Sucesso:</strong> {{ success_rate }}%</li>
                        <li>🕒 <strong>Data da Distribuição:</strong> {{ distribution_date }}</li>
                    </ul>
                </div>
                
                <p>Acesse o dashboard para visualizar os detalhes completos da distribuição.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #6c757d;">Esta é uma notificação automática do Sistema de Distribuição de Submissões.</p>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
    
    def _get_reviewer_notification_template(self) -> Template:
        """Template para notificação de revisores."""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Novas Atribuições</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">📋 Novas Atribuições de Revisão</h2>
                
                <p>Olá <strong>{{ reviewer_name }}</strong>,</p>
                
                <p>Você recebeu {{ assignments_count }} nova(s) atribuição(ões) de revisão para o evento <strong>{{ evento_nome }}</strong>.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">📝 Submissões Atribuídas</h3>
                    {% for assignment in assignments %}
                    <div style="border-left: 3px solid #007bff; padding-left: 10px; margin: 10px 0;">
                        <strong>{{ assignment.title }}</strong><br>
                        <small style="color: #6c757d;">Prazo: {{ assignment.deadline }} | ID: {{ assignment.submission_id }}</small>
                    </div>
                    {% endfor %}
                </div>
                
                <p>Acesse o sistema para iniciar suas revisões.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #6c757d;">Esta é uma notificação automática do Sistema de Distribuição de Submissões.</p>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
    
    def _get_deadline_reminder_template(self) -> Template:
        """Template para lembrete de prazo."""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Lembrete de Prazo</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">⏰ Lembrete: Prazo de Revisão</h2>
                
                <p>Olá <strong>{{ reviewer_name }}</strong>,</p>
                
                <p>Este é um lembrete sobre o prazo de revisão para o evento <strong>{{ evento_nome }}</strong>.</p>
                
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">📝 Submissão Pendente</h3>
                    <p><strong>{{ submission_title }}</strong></p>
                    <p><strong>Prazo:</strong> {{ deadline }}</p>
                    <p><strong>Tempo restante:</strong> {{ days_left }} dia(s)</p>
                    <p><strong>ID da Submissão:</strong> {{ submission_id }}</p>
                </div>
                
                <p>Por favor, acesse o sistema para completar sua revisão antes do prazo.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #6c757d;">Esta é uma notificação automática do Sistema de Distribuição de Submissões.</p>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
    
    def _get_import_completed_template(self) -> Template:
        """Template para notificação de importação concluída."""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Importação Concluída</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #28a745;">📥 Importação de Submissões Concluída</h2>
                
                <p>A importação de submissões foi concluída para o evento <strong>{{ evento_nome }}</strong>.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">📊 Resumo da Importação</h3>
                    <ul style="list-style: none; padding: 0;">
                        <li>📦 <strong>Lote:</strong> {{ batch_id }}</li>
                        <li>📝 <strong>Total Importado:</strong> {{ total_imported }}</li>
                        <li>✅ <strong>Processado:</strong> {{ processed }}</li>
                        <li>❌ <strong>Com Erros:</strong> {{ with_errors }}</li>
                        <li>📈 <strong>Taxa de Sucesso:</strong> {{ success_rate }}%</li>
                        <li>🕒 <strong>Data da Importação:</strong> {{ import_date }}</li>
                    </ul>
                </div>
                
                <p>Acesse o dashboard para visualizar os detalhes e proceder com a distribuição.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #6c757d;">Esta é uma notificação automática do Sistema de Distribuição de Submissões.</p>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
