import importlib
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def relatorio_service_module():
    """Reload relatorio_service with a stubbed transformers pipeline."""
    import sys, types
    sys.modules.pop('services.relatorio_service', None)
    fake_model = MagicMock(return_value=[{"generated_text": "texto gerado"}])
    fake_transformers = types.SimpleNamespace(pipeline=lambda *a, **k: fake_model)
    sys.modules['transformers'] = fake_transformers
    relatorio_service = importlib.import_module('services.relatorio_service')
    yield relatorio_service, fake_model
    sys.modules.pop('transformers', None)


def test_gerar_texto_relatorio(relatorio_service_module):
    service, fake_model = relatorio_service_module
    evento = SimpleNamespace(nome='Evento X')
    texto = service.gerar_texto_relatorio(evento, ['dados'])
    fake_model.assert_called_once()
    assert texto == 'texto gerado'


def test_converter_para_pdf(relatorio_service_module):
    service, _ = relatorio_service_module

    def fake_convert(input_path, output_path):
        with open(output_path, 'wb') as f:
            f.write(b'%PDF-1.4')

    with patch('services.relatorio_service.docx2pdf_convert', side_effect=fake_convert):
        pdf = service.converter_para_pdf(BytesIO(b'docx'))

    assert pdf.getvalue().startswith(b'%PDF')
