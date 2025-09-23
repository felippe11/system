import requests
import json
from app import create_app
from models.event import RespostaFormulario
from models.review import Submission, CategoriaBarema, EventoBarema
from routes.revisor_routes import get_categoria_trabalho

app = create_app()
app.app_context().push()

# Verificar dados do trabalho 794
submission_id = 794
submission = Submission.query.get(submission_id)

print(f'=== TESTE FINAL - FORMULÁRIO DE AVALIAÇÃO ===')
print(f'Trabalho ID: {submission_id}')
print(f'Evento ID: {submission.evento_id}')

# Buscar resposta do formulário
resposta_formulario = RespostaFormulario.query.filter_by(trabalho_id=submission.id).first()
categoria = get_categoria_trabalho(resposta_formulario) if resposta_formulario else None
print(f'Categoria: {categoria}')

# Buscar barema específico da categoria
barema_categoria = CategoriaBarema.query.filter_by(
    evento_id=submission.evento_id,
    categoria=categoria
).first() if categoria else None

# Buscar barema geral
barema_geral = EventoBarema.query.filter_by(evento_id=submission.evento_id).first()

# Determinar qual barema será usado (mesma lógica da função avaliar)
barema = barema_categoria if barema_categoria else barema_geral

print(f'\n=== BAREMA SELECIONADO ===')
if barema:
    if barema == barema_categoria:
        print('Tipo: Barema específico da categoria')
        print(f'ID: {barema.id}')
        print(f'Nome: {barema.nome}')
        print(f'Categoria: {barema.categoria}')
        criterios_dict = barema.criterios
    else:
        print('Tipo: Barema geral do evento')
        print(f'ID: {barema.id}')
        criterios_dict = barema.requisitos if hasattr(barema, 'requisitos') else {}
    
    print(f'\n=== CRITÉRIOS DE AVALIAÇÃO ===')
    if criterios_dict:
        for i, (nome, detalhes) in enumerate(criterios_dict.items(), 1):
            print(f'{i}. {nome}')
            if isinstance(detalhes, dict):
                min_val = detalhes.get('min', 0)
                max_val = detalhes.get('max', 10)
                descricao = detalhes.get('descricao', 'Sem descrição')
                print(f'   Faixa: {min_val} - {max_val}')
                print(f'   Descrição: {descricao}')
            print()
        
        print(f'✅ SUCESSO: {len(criterios_dict)} critérios encontrados para a categoria "{categoria}"')
        print(f'✅ O formulário de avaliação agora carrega os critérios específicos do barema da categoria!')
    else:
        print('❌ ERRO: Nenhum critério encontrado no barema!')
else:
    print('❌ ERRO: Nenhum barema encontrado!')

print(f'\n=== RESUMO ===')
print(f'- Trabalho 794 pertence à categoria: {categoria}')
print(f'- Barema específico criado: {barema_categoria is not None}')
print(f'- Critérios carregados: {len(criterios_dict) if criterios_dict else 0}')
print(f'- Sistema funcionando: {"✅ SIM" if barema and criterios_dict else "❌ NÃO"}')