from datetime import date, datetime

DIAS_SEMANA = {
    0: 'Domingo',
    1: 'Segunda-feira',
    2: 'Terça-feira',
    3: 'Quarta-feira',
    4: 'Quinta-feira',
    5: 'Sexta-feira',
    6: 'Sábado',
}

ENGLISH_TO_NUM = {
    'Sunday': 0,
    'Monday': 1,
    'Tuesday': 2,
    'Wednesday': 3,
    'Thursday': 4,
    'Friday': 5,
    'Saturday': 6,
}


def dia_semana(valor: datetime | date | int | str) -> str:
    """Retorna o nome do dia da semana em português.

    Aceita uma data, ``datetime`` ou um valor numérico (``int`` ou ``str``)
    representando o dia da semana onde ``0`` é domingo e ``6`` é sábado.
    Também suporta nomes dos dias em inglês.
    """

    if isinstance(valor, str):
        if valor.isdigit():
            valor = int(valor)
        else:
            valor = ENGLISH_TO_NUM.get(valor, valor)

    if isinstance(valor, int):
        return DIAS_SEMANA.get(valor, str(valor))

    if isinstance(valor, (datetime, date)):
        indice = (valor.weekday() + 1) % 7
        return DIAS_SEMANA.get(indice, str(indice))

    return str(valor)
