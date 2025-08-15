from datetime import date, datetime

DIAS_SEMANA = {
    'Monday': 'Segunda-feira',
    'Tuesday': 'Terça-feira',
    'Wednesday': 'Quarta-feira',
    'Thursday': 'Quinta-feira',
    'Friday': 'Sexta-feira',
    'Saturday': 'Sábado',
    'Sunday': 'Domingo',
}

def dia_semana(valor: datetime | date | str) -> str:
    """Retorna o nome do dia da semana em português.

    Aceita uma data ou uma string contendo o nome do dia em inglês.
    """
    if isinstance(valor, str):
        nome_em_ingles = valor
    else:
        nome_em_ingles = valor.strftime('%A')
    return DIAS_SEMANA.get(nome_em_ingles, nome_em_ingles)
