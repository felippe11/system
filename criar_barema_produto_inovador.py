from app import create_app
from models.review import CategoriaBarema
from extensions import db

app = create_app()
app.app_context().push()

# Verificar se já existe barema para 'Produto Inovador'
barema_existente = CategoriaBarema.query.filter_by(
    evento_id=2,
    categoria='Produto Inovador'
).first()

if barema_existente:
    print('Barema para "Produto Inovador" já existe!')
    print(f'ID: {barema_existente.id}')
    print(f'Critérios: {barema_existente.criterios}')
else:
    print('Criando barema para categoria "Produto Inovador"...')
    
    # Definir critérios específicos para Produto Inovador
    criterios = {
        "Inovação e Originalidade": {
            "min": 1,
            "max": 10,
            "descricao": "Avalia o grau de inovação e originalidade do produto apresentado"
        },
        "Viabilidade Técnica": {
            "min": 1,
            "max": 10,
            "descricao": "Avalia a viabilidade técnica de implementação do produto"
        },
        "Impacto Educacional": {
            "min": 1,
            "max": 10,
            "descricao": "Avalia o potencial impacto educacional do produto"
        },
        "Apresentação e Documentação": {
            "min": 1,
            "max": 10,
            "descricao": "Avalia a qualidade da apresentação e documentação do produto"
        }
    }
    
    # Criar o barema
    novo_barema = CategoriaBarema(
        evento_id=2,
        categoria='Produto Inovador',
        nome='Barema para Produtos Inovadores',
        descricao='Critérios específicos para avaliação de produtos inovadores',
        criterios=criterios
    )
    
    db.session.add(novo_barema)
    db.session.commit()
    
    print(f'Barema criado com sucesso! ID: {novo_barema.id}')
    print(f'Critérios: {novo_barema.criterios}')

print('\n=== VERIFICAÇÃO FINAL ===')
barema_final = CategoriaBarema.query.filter_by(
    evento_id=2,
    categoria='Produto Inovador'
).first()
print(f'Barema para "Produto Inovador" existe: {barema_final is not None}')
if barema_final:
    print(f'ID: {barema_final.id}')
    print(f'Nome: {barema_final.nome}')
    print(f'Critérios: {list(barema_final.criterios.keys())}')