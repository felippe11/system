import importlib.util
import pathlib

# Load arquivo_utils module directly to avoid importing utils.__init__
file_path = pathlib.Path(__file__).resolve().parents[1] / 'utils' / 'arquivo_utils.py'
spec = importlib.util.spec_from_file_location('arquivo_utils', file_path)
arquivo_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arquivo_utils)

arquivo_permitido = arquivo_utils.arquivo_permitido


def test_arquivo_permitido_extensoes_aceitas():
    assert arquivo_permitido('dados.csv')
    assert arquivo_permitido('planilha.xlsx')
    assert arquivo_permitido('relatorio.XLS')


def test_arquivo_permitido_extensoes_rejeitadas():
    assert not arquivo_permitido('imagem.png')
    assert not arquivo_permitido('documento.pdf')
    assert not arquivo_permitido('arquivo.txt')


def test_determinar_turno():
    import os
    os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
    os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")
    from utils.time_helpers import determinar_turno
    from pytz import timezone
    from datetime import datetime

    tz = timezone("America/Sao_Paulo")
    manha = tz.localize(datetime(2024, 1, 1, 8, 0))
    tarde = tz.localize(datetime(2024, 1, 1, 15, 0))
    noite = tz.localize(datetime(2024, 1, 1, 20, 0))

    assert determinar_turno(manha) == "Matutino"
    assert determinar_turno(tarde) == "Vespertino"
    assert determinar_turno(noite) == "Noturno"


def test_preco_com_taxa_falsy_base(monkeypatch, caplog):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "dummy")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "dummy")

    import importlib.util, pathlib, logging
    spec = importlib.util.spec_from_file_location(
        "utils", pathlib.Path(__file__).resolve().parents[1] / "utils" / "__init__.py"
    )
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)

    caplog.set_level(logging.DEBUG)
    result = utils.preco_com_taxa(0)

    from decimal import Decimal
    assert result == Decimal("0.00")
    assert "Calculando preço com taxa" not in caplog.text
