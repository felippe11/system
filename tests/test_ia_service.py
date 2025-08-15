from types import SimpleNamespace

from services.ia_service import gerar_texto_relatorio


def test_gerar_texto_relatorio_composto():
    evento = SimpleNamespace(nome='Evento Teste')
    dados = {
        'evento': evento,
        'atividades': [1, 2],
        'num_inscritos': 5
    }
    texto = gerar_texto_relatorio(dados)
    assert 'Relatório do evento Evento Teste.' in texto
    assert 'O evento contou com 2 atividade(s).' in texto
    assert 'Número de inscritos: 5.' in texto
