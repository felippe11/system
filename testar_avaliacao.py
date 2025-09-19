from app import create_app
from models.event import RespostaFormulario
from models.review import Submission, CategoriaBarema, EventoBarema
from routes.revisor_routes import get_categoria_trabalho

app = create_app()
app.app_context().push()

# Testar o trabalho 794
submission_id = 794
submission = Submission.query.get(submission_id)

if not submission:
    print(f'Trabalho {submission_id} não encontrado!')
    exit(1)

print(f'=== TESTE DE AVALIAÇÃO - TRABALHO {submission_id} ===')
print(f'Evento ID: {submission.evento_id}')

# Buscar resposta do formulário
resposta_formulario = RespostaFormulario.query.filter_by(trabalho_id=submission.id).first()

if resposta_formulario:
    categoria = get_categoria_trabalho(resposta_formulario)
    print(f'Categoria do trabalho: {categoria}')
    
    # Buscar barema específico da categoria
    barema_categoria = CategoriaBarema.query.filter_by(
        evento_id=submission.evento_id,
        categoria=categoria
    ).first()
    
    # Buscar barema geral
    barema_geral = EventoBarema.query.filter_by(evento_id=submission.evento_id).first()
    
    print(f'\nBarema específico encontrado: {barema_categoria is not None}')
    if barema_categoria:
        print(f'  - ID: {barema_categoria.id}')
        print(f'  - Nome: {barema_categoria.nome}')
        print(f'  - Critérios: {list(barema_categoria.criterios.keys())}')
        print(f'  - Detalhes dos critérios:')
        for criterio, detalhes in barema_categoria.criterios.items():
            print(f'    * {criterio}: {detalhes}')
    
    print(f'\nBarema geral encontrado: {barema_geral is not None}')
    if barema_geral:
        print(f'  - ID: {barema_geral.id}')
        print(f'  - Nome: {barema_geral.nome}')
        if hasattr(barema_geral, 'criterios') and barema_geral.criterios:
            print(f'  - Critérios: {list(barema_geral.criterios.keys())}')
        elif hasattr(barema_geral, 'requisitos') and barema_geral.requisitos:
            print(f'  - Requisitos: {list(barema_geral.requisitos.keys())}')
    
    # Determinar qual barema será usado
    barema = barema_categoria if barema_categoria else barema_geral
    print(f'\n=== BAREMA SELECIONADO ===')
    if barema:
        print(f'Tipo: {"Específico da categoria" if barema == barema_categoria else "Geral do evento"}')
        print(f'ID: {barema.id}')
        print(f'Nome: {barema.nome}')
        
        # Verificar se tem criterios ou requisitos
        criterios_dict = None
        if hasattr(barema, 'criterios') and barema.criterios:
            criterios_dict = barema.criterios
            print(f'Critérios (campo criterios): {list(criterios_dict.keys())}')
        elif hasattr(barema, 'requisitos') and barema.requisitos:
            criterios_dict = barema.requisitos
            print(f'Critérios (campo requisitos): {list(criterios_dict.keys())}')
        
        if criterios_dict:
            print('\nDetalhes dos critérios:')
            for nome, detalhes in criterios_dict.items():
                print(f'  - {nome}: {detalhes}')
        else:
            print('ERRO: Nenhum critério encontrado no barema!')
    else:
        print('ERRO: Nenhum barema encontrado!')
else:
    print('Resposta do formulário não encontrada!')