# utils/time_helpers.py
from datetime import datetime
from pytz import timezone

def formatar_brasilia(dt: datetime | None = None,
                      fmt: str = "%d/%m/%Y %H:%M") -> str:
    """
    Converte `dt` (UTC ou naive) para o fuso de Brasília
    e devolve como string formatada.
    """
    tz_brasilia = timezone("America/Sao_Paulo")
    if dt is None:
        dt = datetime.utcnow()
    return dt.astimezone(tz_brasilia).strftime(fmt)
