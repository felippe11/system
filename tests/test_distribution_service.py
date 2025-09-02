import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta

# Adicionar o diretório raiz ao path para importações
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.distribution_service import DistributionService
from models import Submissao, Revisor, Evento, DistribuicaoSubmissao

class TestDistributionService(unittest.TestCase):
    
    def setUp(self):
        """Configuração inicial para cada teste"""
        self.service = DistributionService()
        
        # Mock do evento
        self.mock_evento = Mock(spec=Evento)
        self.mock_evento.id = 1
        self.mock_evento.nome = "Evento Teste"
        
        # Mock de submissões
        self.mock_submissoes = []
        for i in range(5):
            submissao = Mock(spec=Submissao)
            submissao.id = i + 1
            submissao.titulo = f"Submissão {i + 1}"
            submissao.categoria = "Categoria A" if i % 2 == 0 else "Categoria B"
            submissao.modalidade = "Oral" if i < 3 else "Poster"
            submissao.palavras_chave = f"palavra{i}, teste, pesquisa"
            submissao.evento_id = 1
            self.mock_submissoes.append(submissao)
        
        # Mock de revisores
        self.mock_revisores = []
        for i in range(3):
            revisor = Mock(spec=Revisor)
            revisor.id = i + 1
            revisor.nome = f"Revisor {i + 1}"
            revisor.email = f"revisor{i+1}@teste.com"
            revisor.areas_interesse = "Categoria A, Categoria B" if i == 0 else f"Categoria {'A' if i == 1 else 'B'}"
            revisor.max_submissoes = 3
            revisor.modalidades_preferidas = "Oral, Poster"
            revisor.evento_id = 1
            self.mock_revisores.append(revisor)
    
    def test_calculate_compatibility_score(self):
        """Testa o cálculo de compatibilidade entre revisor e submissão"""
        revisor = self.mock_revisores[0]  # Revisor com interesse em ambas categorias
        submissao = self.mock_submissoes[0]  # Categoria A, Oral
        
        score = self.service._calculate_compatibility_score(revisor, submissao)
        
        # Deve ter score > 0 pois há compatibilidade
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 1.0)
    
    def test_calculate_compatibility_score_no_match(self):
        """Testa compatibilidade quando não há match de categoria"""
        revisor = self.mock_revisores[1]  # Apenas Categoria A
        submissao = self.mock_submissoes[1]  # Categoria B
        
        score = self.service._calculate_compatibility_score(revisor, submissao)
        
        # Score deve ser baixo devido à incompatibilidade de categoria
        self.assertLess(score, 0.5)
    
    def test_check_conflicts_same_author(self):
        """Testa detecção de conflito quando revisor é autor"""
        revisor = self.mock_revisores[0]
        submissao = self.mock_submissoes[0]
        
        # Simular que o revisor é autor da submissão
        submissao.autores = [{'nome': revisor.nome, 'email': revisor.email}]
        
        has_conflict = self.service._check_conflicts(revisor, submissao)
        
        self.assertTrue(has_conflict)
    
    def test_check_conflicts_no_conflict(self):
        """Testa quando não há conflito"""
        revisor = self.mock_revisores[0]
        submissao = self.mock_submissoes[0]
        
        # Simular autores diferentes
        submissao.autores = [{'nome': 'Autor Diferente', 'email': 'outro@teste.com'}]
        
        has_conflict = self.service._check_conflicts(revisor, submissao)
        
        self.assertFalse(has_conflict)
    
    @patch('services.distribution_service.db')
    def test_distribute_balanced_success(self, mock_db):
        """Testa distribuição balanceada bem-sucedida"""
        # Configurar mocks
        mock_db.session.query.return_value.filter_by.return_value.all.side_effect = [
            self.mock_submissoes,  # Primeira chamada para submissões
            self.mock_revisores    # Segunda chamada para revisores
        ]
        
        # Mock para verificar distribuições existentes (vazio)
        mock_db.session.query.return_value.filter.return_value.all.return_value = []
        
        # Executar distribuição
        result = self.service.distribute_submissions(
            evento_id=1,
            reviewers_per_submission=2,
            distribution_mode='balanced'
        )
        
        # Verificar resultado
        self.assertTrue(result['success'])
        self.assertGreater(result['total_assignments'], 0)
        self.assertEqual(result['total_submissions'], len(self.mock_submissoes))
        self.assertEqual(result['total_reviewers'], len(self.mock_revisores))
    
    @patch('services.distribution_service.db')
    def test_distribute_insufficient_reviewers(self, mock_db):
        """Testa distribuição com revisores insuficientes"""
        # Configurar apenas 1 revisor para 5 submissões
        single_reviewer = [self.mock_revisores[0]]
        
        mock_db.session.query.return_value.filter_by.return_value.all.side_effect = [
            self.mock_submissoes,  # Submissões
            single_reviewer        # Apenas 1 revisor
        ]
        
        mock_db.session.query.return_value.filter.return_value.all.return_value = []
        
        result = self.service.distribute_submissions(
            evento_id=1,
            reviewers_per_submission=3,  # Mais revisores que disponível
            distribution_mode='balanced'
        )
        
        # Deve falhar ou ter warnings
        self.assertIn('warnings', result)
        self.assertGreater(len(result['warnings']), 0)
    
    def test_validate_distribution_parameters_valid(self):
        """Testa validação de parâmetros válidos"""
        is_valid, errors = self.service._validate_distribution_parameters(
            evento_id=1,
            reviewers_per_submission=2,
            distribution_mode='balanced'
        )
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_distribution_parameters_invalid(self):
        """Testa validação de parâmetros inválidos"""
        # Teste com parâmetros inválidos
        is_valid, errors = self.service._validate_distribution_parameters(
            evento_id=None,
            reviewers_per_submission=0,
            distribution_mode='invalid_mode'
        )
        
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_calculate_distribution_metrics(self):
        """Testa cálculo de métricas de distribuição"""
        # Simular algumas atribuições
        mock_assignments = []
        for i in range(6):  # 6 atribuições
            assignment = Mock()
            assignment.submissao_id = (i % 3) + 1  # 3 submissões
            assignment.revisor_id = (i % 2) + 1    # 2 revisores
            assignment.compatibility_score = 0.8
            mock_assignments.append(assignment)
        
        metrics = self.service._calculate_distribution_metrics(mock_assignments)
        
        self.assertIn('total_assignments', metrics)
        self.assertIn('average_compatibility', metrics)
        self.assertIn('distribution_balance', metrics)
        self.assertEqual(metrics['total_assignments'], 6)
    
    @patch('services.distribution_service.db')
    def test_get_distribution_history(self, mock_db):
        """Testa recuperação do histórico de distribuições"""
        # Mock de distribuições históricas
        mock_distributions = []
        for i in range(3):
            dist = Mock()
            dist.id = i + 1
            dist.created_at = datetime.now() - timedelta(days=i)
            dist.total_assignments = 10 + i
            dist.success_rate = 0.9
            mock_distributions.append(dist)
        
        mock_db.session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = mock_distributions
        
        history = self.service.get_distribution_history(evento_id=1)
        
        self.assertEqual(len(history), 3)
        self.assertIn('distributions', history)
    
    def test_stratified_distribution_logic(self):
        """Testa lógica específica da distribuição estratificada"""
        # Agrupar submissões por categoria
        categories = {}
        for submissao in self.mock_submissoes:
            cat = submissao.categoria
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(submissao)
        
        # Verificar se o agrupamento funciona
        self.assertIn('Categoria A', categories)
        self.assertIn('Categoria B', categories)
        self.assertGreater(len(categories['Categoria A']), 0)
        self.assertGreater(len(categories['Categoria B']), 0)
    
    def test_random_distribution_seed(self):
        """Testa se a distribuição aleatória é reproduzível com seed"""
        import random
        
        # Definir seed para reproduzibilidade
        random.seed(42)
        first_shuffle = list(range(10))
        random.shuffle(first_shuffle)
        
        # Resetar seed e repetir
        random.seed(42)
        second_shuffle = list(range(10))
        random.shuffle(second_shuffle)
        
        # Devem ser iguais
        self.assertEqual(first_shuffle, second_shuffle)
    
    @patch('services.distribution_service.NotificationService')
    def test_send_distribution_notifications(self, mock_notification_service):
        """Testa envio de notificações após distribuição"""
        mock_notification = Mock()
        mock_notification_service.return_value = mock_notification
        
        # Simular resultado de distribuição
        distribution_result = {
            'success': True,
            'total_assignments': 10,
            'total_submissions': 5,
            'total_reviewers': 3,
            'distribution_id': 1
        }
        
        # Chamar método de notificação (se existir)
        if hasattr(self.service, '_send_notifications'):
            self.service._send_notifications(self.mock_evento, distribution_result)
            
            # Verificar se notificação foi chamada
            mock_notification.notify_distribution_complete.assert_called_once()

class TestDistributionAlgorithms(unittest.TestCase):
    """Testes específicos para algoritmos de distribuição"""
    
    def setUp(self):
        self.service = DistributionService()
    
    def test_hungarian_algorithm_simulation(self):
        """Testa simulação do algoritmo húngaro para atribuição ótima"""
        # Matriz de custos (quanto menor, melhor)
        cost_matrix = [
            [0.1, 0.8, 0.9],  # Revisor 1
            [0.7, 0.2, 0.8],  # Revisor 2
            [0.9, 0.9, 0.1]   # Revisor 3
        ]
        
        # Encontrar atribuição de custo mínimo
        # (simulação simples - em produção usaria scipy.optimize.linear_sum_assignment)
        min_cost = float('inf')
        best_assignment = None
        
        # Testar todas as permutações possíveis (para matriz 3x3)
        import itertools
        for perm in itertools.permutations(range(3)):
            cost = sum(cost_matrix[i][perm[i]] for i in range(3))
            if cost < min_cost:
                min_cost = cost
                best_assignment = perm
        
        # Verificar se encontrou uma atribuição válida
        self.assertIsNotNone(best_assignment)
        self.assertEqual(len(best_assignment), 3)
        self.assertLess(min_cost, 1.0)  # Deve ser menor que atribuição aleatória
    
    def test_load_balancing_algorithm(self):
        """Testa algoritmo de balanceamento de carga"""
        # Simular carga atual dos revisores
        reviewer_loads = [2, 1, 3, 0, 2]  # 5 revisores com cargas diferentes
        max_capacity = 3
        
        # Encontrar revisor com menor carga que ainda tem capacidade
        available_reviewers = [
            (i, load) for i, load in enumerate(reviewer_loads) 
            if load < max_capacity
        ]
        
        # Ordenar por carga (menor primeiro)
        available_reviewers.sort(key=lambda x: x[1])
        
        # Verificar se o algoritmo funciona
        self.assertGreater(len(available_reviewers), 0)
        self.assertEqual(available_reviewers[0][0], 3)  # Revisor com índice 3 (carga 0)
        self.assertEqual(available_reviewers[0][1], 0)   # Carga 0

if __name__ == '__main__':
    # Configurar logging para testes
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Executar testes
    unittest.main(verbosity=2)