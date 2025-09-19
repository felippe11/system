from app import create_app
from models.review import CategoriaBarema, EventoBarema, Submission
from models.event import RespostaFormulario

app = create_app()
app.app_context().push()

# Verificar o trabalho 794
submission = Submission.query.get(794)
print(f'Trabalho 794 - Evento ID: {submission.evento_id if submission else "Não encontrado"}')

if submission:
    print(f'Evento ID: {submission.evento_id}')
    
    # Verificar baremas de categoria
    baremas_categoria = CategoriaBarema.query.filter_by(evento_id=submission.evento_id).all()
    print(f'Baremas categoria: {len(baremas_categoria)}')
    for barema in baremas_categoria:
        print(f'  - Categoria: {barema.categoria}, ID: {barema.id}')
    
    # Verificar baremas gerais
    baremas_gerais = EventoBarema.query.filter_by(evento_id=submission.evento_id).all()
    print(f'Baremas gerais: {len(baremas_gerais)}')
    for barema in baremas_gerais:
        print(f'  - ID: {barema.id}')
    
    # Verificar resposta do formulário
    resposta_formulario = RespostaFormulario.query.filter_by(trabalho_id=submission.id).first()
    print(f'Resposta formulário encontrada: {resposta_formulario is not None}')
    
    if resposta_formulario:
        # Verificar categoria do trabalho
        categoria = None
        for resposta_campo in resposta_formulario.respostas_campos:
            if resposta_campo.campo.nome.lower() == 'categoria':
                categoria = resposta_campo.valor
                break
        print(f'Categoria do trabalho: {categoria}')
        
        # Verificar se existe barema para essa categoria
        if categoria:
            barema_categoria = CategoriaBarema.query.filter_by(
                evento_id=submission.evento_id,
                categoria=categoria
            ).first()
            print(f'Barema específico para categoria "{categoria}": {barema_categoria is not None}')
else:
    print('Trabalho 794 não encontrado!')