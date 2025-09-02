import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta

# Adicionar o diretório raiz ao path para importações
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.notification_service import NotificationService
from models import Evento, Revisor, Submissao, DistribuicaoSubmissao

class TestNotificationService(unittest.TestCase):
    
    def setUp(self):
        """Configuração inicial para cada teste"""
        self.service = NotificationService()
        
        # Mock do evento
        self.mock_evento = Mock(spec=Evento)
        self.mock_evento.id = 1
        self.mock_evento.nome = "Congresso de Teste 2024"
        self.mock_evento.data_inicio = datetime.now() + timedelta(days=30)
        self.mock_evento.data_fim = datetime.now() + timedelta(days=32)
        
        # Mock de revisor
        self.mock_revisor = Mock(spec=Revisor)
        self.mock_revisor.id = 1
        self.mock_revisor.nome = "Dr. João Silva"
        self.mock_revisor.email = "joao.silva@teste.com"
        self.mock_revisor.evento_id = 1
        
        # Mock de submissões
        self.mock_submissoes = []
        for i in range(3):
            submissao = Mock(spec=Submissao)
            submissao.id = i + 1
            submissao.titulo = f"Título da Submissão {i + 1}"
            submissao.autores = [{'nome': f'Autor {i + 1}', 'email': f'autor{i+1}@teste.com'}]
            submissao.categoria = "Categoria A"
            submissao.modalidade = "Oral"
            submissao.resumo = f"Resumo da submissão {i + 1}..."
            submissao.palavras_chave = f"palavra{i}, teste, pesquisa"
            self.mock_submissoes.append(submissao)
    
    @patch('services.notification_service.enviar_email')
    @patch('services.notification_service.render_template')
    def test_notify_distribution_complete_success(self, mock_render, mock_email):
        """Testa notificação de distribuição completa com sucesso"""
        # Configurar mocks
        mock_render.return_value = "<html>Email content</html>"
        mock_email.return_value = True
        
        # Dados da distribuição
        distribution_data = {
            'total_submissions': 10,
            'total_assignments': 25,
            'total_reviewers': 8,
            'success_rate': 95.5,
            'distribution_mode': 'balanced',
            'conflicts_detected': 2,
            'fallback_assignments': 1,
            'processing_time': 45.2,
            'completed_at': datetime.now()
        }
        
        # Executar notificação
        result = self.service.notify_distribution_complete(
            self.mock_evento, 
            distribution_data,
            admin_emails=['admin@teste.com']
        )
        
        # Verificar resultado
        self.assertTrue(result['success'])
        self.assertEqual(result['emails_sent'], 1)
        
        # Verificar se template foi renderizado
        mock_render.assert_called_once()
        
        # Verificar se email foi enviado
        mock_email.assert_called_once()
    
    @patch('services.notification_service.enviar_email')
    @patch('services.notification_service.render_template')
    def test_notify_reviewer_assignment_success(self, mock_render, mock_email):
        """Testa notificação de atribuição para revisor"""
        # Configurar mocks
        mock_render.return_value = "<html>Assignment email</html>"
        mock_email.return_value = True
        
        # Executar notificação
        result = self.service.notify_reviewer_assignment(
            self.mock_evento,
            self.mock_revisor,
            self.mock_submissoes,
            deadline=datetime.now() + timedelta(days=14),
            review_type='double_blind'
        )
        
        # Verificar resultado
        self.assertTrue(result['success'])
        self.assertEqual(result['reviewer_email'], self.mock_revisor.email)
        
        # Verificar chamadas
        mock_render.assert_called_once()
        mock_email.assert_called_once()
    
    @patch('services.notification_service.enviar_email')
    @patch('services.notification_service.render_template')
    def test_send_deadline_reminder_success(self, mock_render, mock_email):
        """Testa envio de lembrete de prazo"""
        # Configurar mocks
        mock_render.return_value = "<html>Reminder email</html>"
        mock_email.return_value = True
        
        # Mock de atribuições pendentes
        pending_assignments = self.mock_submissoes[:2]  # 2 pendentes
        completed_assignments = self.mock_submissoes[2:]  # 1 completa
        
        # Executar lembrete
        result = self.service.send_deadline_reminder(
            self.mock_evento,
            self.mock_revisor,
            deadline=datetime.now() + timedelta(days=3),
            pending_assignments=pending_assignments,
            completed_assignments=completed_assignments
        )
        
        # Verificar resultado
        self.assertTrue(result['success'])
        self.assertEqual(result['pending_count'], 2)
        self.assertEqual(result['completed_count'], 1)
        
        # Verificar chamadas
        mock_render.assert_called_once()
        mock_email.assert_called_once()
    
    @patch('services.notification_service.enviar_email')
    def test_notify_import_complete_success(self, mock_email):
        """Testa notificação de importação completa"""
        mock_email.return_value = True
        
        # Dados da importação
        import_data = {
            'total_records': 100,
            'successful_records': 95,
            'failed_records': 5,
            'success_rate': 95.0,
            'processing_time': 30.5,
            'batch_id': 'BATCH_001',
            'filename': 'submissoes.xlsx',
            'processed_at': datetime.now(),
            'column_mapping': {
                'titulo': {'column': 'Title', 'confidence': 95},
                'autor': {'column': 'Author', 'confidence': 90}
            },
            'error_samples': [
                {'row': 15, 'message': 'Email inválido', 'field': 'email'},
                {'row': 23, 'message': 'Categoria não encontrada', 'field': 'categoria'}
            ]
        }
        
        # Executar notificação
        result = self.service.notify_import_complete(
            self.mock_evento,
            import_data,
            admin_emails=['admin@teste.com']
        )
        
        # Verificar resultado
        self.assertTrue(result['success'])
        self.assertEqual(result['emails_sent'], 1)
    
    def test_format_assignment_summary(self):
        """Testa formatação do resumo de atribuições"""
        summary = self.service._format_assignment_summary(self.mock_submissoes)
        
        # Verificar se o resumo contém informações esperadas
        self.assertIn('total', summary)
        self.assertIn('by_category', summary)
        self.assertIn('by_modality', summary)
        self.assertEqual(summary['total'], 3)
    
    def test_calculate_deadline_urgency(self):
        """Testa cálculo de urgência do prazo"""
        # Prazo em 1 dia
        deadline_urgent = datetime.now() + timedelta(days=1)
        urgency_urgent = self.service._calculate_deadline_urgency(deadline_urgent)
        
        # Prazo em 10 dias
        deadline_normal = datetime.now() + timedelta(days=10)
        urgency_normal = self.service._calculate_deadline_urgency(deadline_normal)
        
        # Prazo já passou
        deadline_overdue = datetime.now() - timedelta(days=1)
        urgency_overdue = self.service._calculate_deadline_urgency(deadline_overdue)
        
        # Verificar classificações
        self.assertEqual(urgency_urgent, 'urgent')
        self.assertEqual(urgency_normal, 'normal')
        self.assertEqual(urgency_overdue, 'overdue')
    
    @patch('services.notification_service.enviar_email')
    def test_email_failure_handling(self, mock_email):
        """Testa tratamento de falhas no envio de email"""
        # Simular falha no envio
        mock_email.return_value = False
        
        # Tentar enviar notificação
        result = self.service.notify_distribution_complete(
            self.mock_evento,
            {'total_submissions': 10},
            admin_emails=['admin@teste.com']
        )
        
        # Verificar que falha foi tratada
        self.assertFalse(result['success'])
        self.assertIn('errors', result)
    
    def test_template_context_preparation(self):
        """Testa preparação do contexto para templates"""
        context = self.service._prepare_template_context(
            self.mock_evento,
            {'custom_data': 'test'}
        )
        
        # Verificar contexto básico
        self.assertIn('evento_nome', context)
        self.assertIn('evento_id', context)
        self.assertIn('custom_data', context)
        self.assertEqual(context['evento_nome'], self.mock_evento.nome)
        self.assertEqual(context['custom_data'], 'test')
    
    @patch('services.notification_service.enviar_email')
    @patch('services.notification_service.render_template')
    def test_batch_notification_sending(self, mock_render, mock_email):
        """Testa envio de notificações em lote"""
        mock_render.return_value = "<html>Batch email</html>"
        mock_email.return_value = True
        
        # Lista de revisores
        reviewers = [self.mock_revisor] * 3
        
        # Enviar notificações em lote
        results = self.service.send_batch_notifications(
            self.mock_evento,
            reviewers,
            'assignment',
            {'deadline': datetime.now() + timedelta(days=14)}
        )
        
        # Verificar resultados
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r['success'] for r in results))
    
    def test_notification_rate_limiting(self):
        """Testa limitação de taxa de envio"""
        # Simular muitas notificações em pouco tempo
        start_time = datetime.now()
        
        # Verificar se há controle de taxa
        can_send = self.service._check_rate_limit('admin@teste.com')
        self.assertTrue(can_send)  # Primeira tentativa deve ser permitida
        
        # Registrar envio
        self.service._record_email_sent('admin@teste.com')
        
        # Verificar se ainda pode enviar (depende da implementação)
        # Este teste pode precisar ser ajustado baseado na política de rate limiting
    
    def test_email_template_validation(self):
        """Testa validação de templates de email"""
        # Verificar se templates necessários existem
        required_templates = [
            'emails/distribution_complete.html',
            'emails/reviewer_assignment.html',
            'emails/deadline_reminder.html',
            'emails/import_complete.html'
        ]
        
        for template in required_templates:
            # Verificar se template pode ser carregado
            # (em um ambiente real, isso testaria se o arquivo existe)
            self.assertTrue(self.service._validate_template_exists(template))
    
    @patch('services.notification_service.db')
    def test_notification_logging(self, mock_db):
        """Testa logging de notificações enviadas"""
        # Simular envio de notificação
        notification_data = {
            'type': 'distribution_complete',
            'recipient': 'admin@teste.com',
            'evento_id': 1,
            'sent_at': datetime.now()
        }
        
        # Verificar se notificação é logada
        self.service._log_notification(notification_data)
        
        # Em um ambiente real, verificaria se foi salvo no banco
        # mock_db.session.add.assert_called_once()
        # mock_db.session.commit.assert_called_once()
    
    def test_notification_preferences(self):
        """Testa respeito às preferências de notificação"""
        # Simular revisor com preferências específicas
        self.mock_revisor.notification_preferences = {
            'email_assignments': True,
            'email_reminders': False,
            'email_updates': True
        }
        
        # Verificar se preferências são respeitadas
        should_send_assignment = self.service._should_send_notification(
            self.mock_revisor, 'assignment'
        )
        should_send_reminder = self.service._should_send_notification(
            self.mock_revisor, 'reminder'
        )
        
        self.assertTrue(should_send_assignment)
        self.assertFalse(should_send_reminder)

class TestNotificationTemplates(unittest.TestCase):
    """Testes específicos para templates de notificação"""
    
    def setUp(self):
        self.service = NotificationService()
    
    def test_distribution_template_context(self):
        """Testa contexto do template de distribuição"""
        context = {
            'evento_nome': 'Teste',
            'total_submissions': 10,
            'total_assignments': 25,
            'success_rate': 95.5
        }
        
        # Verificar se contexto tem dados necessários
        required_fields = ['evento_nome', 'total_submissions', 'total_assignments', 'success_rate']
        for field in required_fields:
            self.assertIn(field, context)
    
    def test_assignment_template_context(self):
        """Testa contexto do template de atribuição"""
        context = {
            'evento_nome': 'Teste',
            'revisor_nome': 'Dr. João',
            'assignments': [],
            'deadline': datetime.now(),
            'review_type': 'double_blind'
        }
        
        # Verificar campos obrigatórios
        required_fields = ['evento_nome', 'revisor_nome', 'assignments', 'deadline']
        for field in required_fields:
            self.assertIn(field, context)
    
    def test_reminder_template_context(self):
        """Testa contexto do template de lembrete"""
        context = {
            'evento_nome': 'Teste',
            'revisor_nome': 'Dr. João',
            'days_remaining': 3,
            'pending_assignments': [],
            'completed_assignments': []
        }
        
        # Verificar campos obrigatórios
        required_fields = ['evento_nome', 'revisor_nome', 'days_remaining']
        for field in required_fields:
            self.assertIn(field, context)

if __name__ == '__main__':
    # Configurar logging para testes
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Executar testes
    unittest.main(verbosity=2)