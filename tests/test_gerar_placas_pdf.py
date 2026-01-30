import pytest
import os
from unittest.mock import MagicMock, patch
from datetime import datetime, time
import sys
from unittest.mock import MagicMock, patch

# Set environment variables before importing utils or routes
os.environ['GOOGLE_CLIENT_ID'] = 'dummy_id'
os.environ['GOOGLE_CLIENT_SECRET'] = 'dummy_secret'

# Add the system directory to the path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.pdf_service import gerar_placas_oficinas_pdf

@pytest.fixture
def app():
    from flask import Flask
    app = Flask(__name__, 
                static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static')),
                template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')))
    app.config['TESTING'] = True
    return app

@pytest.fixture
def mock_app_context(app):
    with app.app_context():
        yield app

@pytest.fixture
def mock_db_models():
    # Patch the actual modules where these classes are defined
    with patch('models.Evento') as MockEvento, \
         patch('models.Oficina') as MockOficina, \
         patch('extensions.db') as mock_db:
        
        # Setup Evento
        evento = MagicMock()
        evento.id = 1
        evento.nome = "Evento Teste"
        MockEvento.query.get_or_404.return_value = evento
        
        # Setup Oficina
        oficina = MagicMock()
        oficina.titulo = "Oficina de Design System"
        oficina.local = "Sala 101"
        
        # Ministrante
        ministrante = MagicMock()
        ministrante.nome = "João da Silva"
        ministrante.formacao = "Designer Senior"
        oficina.ministrante_obj = ministrante
        
        # Dias
        dia1 = MagicMock()
        dia1.data = datetime(2026, 1, 30).date()
        dia1.horario_inicio = time(9, 0)
        dia1.horario_fim = time(12, 0)
        
        oficina.dias = [dia1]
        
        # Configure the query chain
        # Oficina.query.filter_by(...).options(...).all()
        mock_query = MockOficina.query
        mock_filter = mock_query.filter_by.return_value
        mock_options = mock_filter.options.return_value
        mock_options.all.return_value = [oficina]
        
        yield

def test_gerar_placas_oficinas_pdf(mock_app_context, mock_db_models):
    # Mock send_file to avoid actual file sending
    with patch('flask.send_file') as mock_send_file:
        # Execute the function
        gerar_placas_oficinas_pdf(1)
        
        # Verification logic
        # Check if file was created in the expected path
        expected_dir = os.path.join(mock_app_context.static_folder, 'placas', '1')
        expected_file = os.path.join(expected_dir, 'placas_oficinas_1.pdf')
        
        assert os.path.exists(expected_file)
        assert os.path.getsize(expected_file) > 0
        
        # Cleanup
        if os.path.exists(expected_file):
            os.remove(expected_file)
            # Try to remove the directory if empty, but don't fail if not
            try:
                os.rmdir(expected_dir)
            except OSError:
                pass
