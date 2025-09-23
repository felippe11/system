import os
import sys
import importlib


def _reload_reportlab():
    """Ensure real reportlab is loaded for PDF generation."""
    for key in list(sys.modules):
        if key.startswith("reportlab"):
            del sys.modules[key]
    return importlib.import_module("reportlab")


def _create_pdf(tmp_path):
    _reload_reportlab()
    from services.declaracao_service import gerar_declaracao_personalizada

    class Usuario:
        id = 1
        nome = "Participante Teste"
        email = "teste@example.com"

    class Evento:
        id = 2
        nome = "Evento Teste"
        data_inicio = None

    class Template:
        conteudo = (
            "Declaramos que {NOME_PARTICIPANTE} participou do evento "
            "{NOME_EVENTO}."
        )

    class Cliente:
        logo_certificado = None

    participacao = {
        "participou": True,
        "total_checkins": 0,
        "atividades": [],
        "carga_horaria_total": 0,
    }

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        rel_path = gerar_declaracao_personalizada(
            Usuario, Evento, participacao, Template, Cliente
        )
        return tmp_path / rel_path
    finally:
        os.chdir(cwd)


def test_gerar_declaracao_cria_arquivo(tmp_path):
    pdf_path = _create_pdf(tmp_path)
    assert pdf_path.exists()


def test_gerar_declaracao_conteudo_pdf(tmp_path):
    pdf_path = _create_pdf(tmp_path)
    with open(pdf_path, "rb") as f:
        header = f.read(4)
    assert header == b"%PDF"
