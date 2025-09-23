from app import create_app
from models.review import CategoriaBarema, EventoBarema
from models import Evento
from extensions import db

app = create_app()
app.app_context().push()

# Verificar baremas existentes
print('=== BAREMAS EXISTENTES ===')
print(f'Total baremas categoria: {CategoriaBarema.query.count()}')
print(f'Total baremas gerais: {EventoBarema.query.count()}')

print('\nEventos com baremas gerais:')
for b in EventoBarema.query.all():
    print(f'  Evento {b.evento_id}')

print('\nEventos com baremas categoria:')
for b in CategoriaBarema.query.all():
    print(f'  Evento {b.evento_id}, Categoria: {b.categoria}')

# Verificar se o evento 2 existe
evento = Evento.query.get(2)
print(f'\nEvento 2 existe: {evento is not None}')
if evento:
    print(f'Nome do evento: {evento.nome}')

# Criar barema geral para o evento 2 se não existir
barema_geral = EventoBarema.query.filter_by(evento_id=2).first()
if not barema_geral and evento:
    print('\n=== CRIANDO BAREMA GERAL PARA EVENTO 2 ===')
    
    # Criar requisitos no formato JSON
    requisitos = {
        'Relevância do tema': {'min': 0, 'max': 10},
        'Qualidade metodológica': {'min': 0, 'max': 10},
        'Clareza da apresentação': {'min': 0, 'max': 10},
        'Contribuição científica': {'min': 0, 'max': 10},
        'Referências bibliográficas': {'min': 0, 'max': 10}
    }
    
    barema_geral = EventoBarema(
        evento_id=2,
        requisitos=requisitos
    )
    db.session.add(barema_geral)
    db.session.commit()
    print(f'Barema geral criado com ID: {barema_geral.id}')
    print(f'Requisitos criados: {len(requisitos)}')
else:
    print('\nBarema geral já existe para o evento 2 ou evento não encontrado')

# Verificar novamente
print('\n=== VERIFICAÇÃO FINAL ===')
barema_geral_final = EventoBarema.query.filter_by(evento_id=2).first()
print(f'Barema geral para evento 2: {barema_geral_final is not None}')
if barema_geral_final:
    print(f'ID do barema: {barema_geral_final.id}')
    print(f'Requisitos: {list(barema_geral_final.requisitos.keys()) if barema_geral_final.requisitos else "Nenhum"}')
    print(f'Total de critérios: {len(barema_geral_final.requisitos) if barema_geral_final.requisitos else 0}')