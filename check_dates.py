from app import create_app
from models import RevisorProcess, Evento
from extensions import db

app = create_app()
with app.app_context():
    processos = RevisorProcess.query.filter_by(exibir_para_participantes=True).all()
    print('=== PROCESSOS SELETIVOS ===')
    for p in processos:
        print(f'ID: {p.id}, Nome: {p.nome}')
        print(f'Availability Start: {p.availability_start}')
        print(f'Availability End: {p.availability_end}')
        print('---')

    print('\n=== EVENTOS ASSOCIADOS ===')
    for p in processos:
        print(f'Processo {p.id} - {p.nome}:')
        for e in p.eventos:
            print(f'  Evento ID:{e.id}, Nome:{e.nome}')
            print(f'  Data Inicio: {e.data_inicio}')
            print(f'  Data Fim: {e.data_fim}')
        print('---')