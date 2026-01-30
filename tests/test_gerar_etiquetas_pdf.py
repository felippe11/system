import pytest
import os
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys

# Add the system directory to the path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.pdf_service import gerar_etiquetas_pdf

@pytest.fixture
def app():
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    return app

@pytest.fixture
def mock_app_context(app):
    with app.app_context():
        yield app

@pytest.fixture
def mock_db_models():
    # Patch the actual modules where these classes are defined
    with patch('models.Evento') as MockEvento, \
         patch('models.Usuario') as MockUsuario, \
         patch('models.Inscricao') as MockInscricao:
         
        # Setup Evento
        evento = MagicMock()
        evento.id = 1
        evento.nome = "Evento de Teste AppFiber"
        evento.data_inicio = datetime(2026, 1, 30)
        evento.data_fim = datetime(2026, 2, 1)
        MockEvento.query.get.return_value = evento
        
        # Setup Users
        user1 = MagicMock()
        user1.id = 101
        user1.nome = "Participante Silva"
        
        user2 = MagicMock()
        user2.id = 102
        user2.nome = "Outra Pessoa Longa da Silva Sauro"
        
        users = [user1, user2]
        
        # Setup Inscricao
        inscricao1 = MagicMock()
        inscricao1.usuario_id = 101
        inscricao1.qr_code_token = "TOKEN123456"
        
        # Mock queries - this logic can be complex depending on how the service queries
        # The service does: 
        # 1. Inscricao.query.filter_by(evento_id=..., cliente_id=...).all() -> returns list of inscricoes
        # 2. Usuario.query.filter(Usuario.id.in_(...)).all() -> returns list of users
        
        MockInscricao.query.filter_by.return_value.all.return_value = [inscricao1]
        MockInscricao.query.filter_by.return_value.first.return_value = inscricao1 # For the loop inside
        
        MockUsuario.query.filter.return_value.all.return_value = users
        
        yield

def test_gerar_etiquetas_pdf(mock_app_context, mock_db_models):
    # Mock send_file to avoid actual file sending
    with patch('flask.send_file') as mock_send_file, \
         patch('services.pdf_service.gerar_qr_code_inscricao') as mock_qr_gen, \
         patch('services.pdf_service.ImageReader') as mock_image_reader:
        
        # Mock QR code generation
        mock_qr_gen.return_value = "dummy_qr_path.png"
        
        # Execute the function (cliente_id=1, evento_id=1)
        # Note: The service expects `evento_id` as second arg
        gerar_etiquetas_pdf(1, 1)
        
        # Verify file creation
        expected_dir = os.path.join(mock_app_context.static_folder, 'etiquetas')
        expected_file = os.path.join(expected_dir, 'etiquetas_evento_1_Evento_de_Teste_AppFiber.pdf')
        
        # The service doesn't return the path directly in `send_file` in the original code, 
        # it might return the result of `send_file`.
        # But we check if the file exists on disk.
        
        assert os.path.exists(expected_dir)
        # Check if any pdf file exists in that dir, specifically the one we expect
        assert os.path.exists(expected_file)
        assert os.path.getsize(expected_file) > 0
        
        # Cleanup
        if os.path.exists(expected_file):
            os.remove(expected_file)
