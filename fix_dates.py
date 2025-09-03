from app import create_app
from models import Evento
from extensions import db
from datetime import datetime, date

app = create_app()
with app.app_context():
    # Corrigir as datas do evento ID 12 que está sendo usado pelos processos
    evento = Evento.query.get(12)
    if evento:
        print(f'Evento atual: {evento.nome}')
        print(f'Data início atual: {evento.data_inicio}')
        print(f'Data fim atual: {evento.data_fim}')
        
        # Definir datas mais realistas (próximas ao período atual)
        evento.data_inicio = date(2025, 9, 15)  # 15/09/2025
        evento.data_fim = date(2025, 9, 30)     # 30/09/2025
        
        db.session.commit()
        
        print(f'Novas datas:')
        print(f'Data início: {evento.data_inicio}')
        print(f'Data fim: {evento.data_fim}')
        print('Datas atualizadas com sucesso!')
    else:
        print('Evento não encontrado')