import random
import pytest
from unittest.mock import Mock
from populate_script import criar_agendamentos_visita


@pytest.fixture
def mock_evento():
    evento = Mock()
    oficina = Mock()
    horario = Mock()

    # Configure mocks
    horario.vagas_disponiveis = 20
    horario.id = 1
    oficina.horarios = [horario]
    evento.oficinas = [oficina]

    return evento


@pytest.fixture
def mock_usuarios():
    professor = Mock()
    professor.tipo = "professor"
    professor.id = 1
    return [professor]


def test_criar_agendamentos_sem_vagas(mock_evento, mock_usuarios):
    # Arrange
    mock_evento.oficinas[0].horarios[0].vagas_disponiveis = 0

    # Act
    resultado = criar_agendamentos_visita([mock_evento], mock_usuarios)

    # Assert
    assert len(resultado) == 0


def test_criar_agendamentos_com_vagas(mock_evento, mock_usuarios):
    # Arrange
    random.seed(42)  # For reproducible results
    mock_evento.oficinas[0].horarios[0].vagas_disponiveis = 20

    # Act
    resultado = criar_agendamentos_visita([mock_evento], mock_usuarios)

    # Assert
    assert len(resultado) > 0
    assert resultado[0].quantidade_alunos <= 20


def test_criar_agendamentos_respeita_limite_maximo(mock_evento, mock_usuarios):
    # Arrange
    mock_evento.oficinas[0].horarios[0].vagas_disponiveis = 50

    # Act
    resultado = criar_agendamentos_visita([mock_evento], mock_usuarios)

    # Assert
    assert all(a.quantidade_alunos <= 30 for a in resultado)
