from app import create_app
from models.event import CampoFormulario, Formulario, RevisorProcess

app = create_app()
with app.app_context():
    # Verificar processos revisores ativos
    processos = RevisorProcess.query.all()
    print('Processos Revisores encontrados:')
    for p in processos:
        print(f'ID: {p.id}, Nome: {p.nome}, Formulário ID: {p.formulario_id}, Status: {p.status}')
    
    print('\nDetalhes dos formulários usados nos processos:')
    for p in processos:
        if p.formulario_id:
            formulario = Formulario.query.get(p.formulario_id)
            if formulario:
                print(f'\nProcesso: {p.nome}')
                print(f'Formulário: {formulario.nome} (ID: {formulario.id})')
                print('Campos:')
                for campo in formulario.campos:
                    print(f'  - {campo.nome} (Tipo: {campo.tipo}, Etapa: {campo.etapa}, Obrigatório: {campo.obrigatorio})')
            else:
                print(f'\nProcesso: {p.nome} - Formulário não encontrado (ID: {p.formulario_id})')
        else:
            print(f'\nProcesso: {p.nome} - Sem formulário associado')