from app import create_app
from models.review import Assignment
from models.event import RespostaFormulario
from models.user import Usuario

app = create_app()
with app.app_context():
    # Verificar se existe assignment para o trabalho 794
    assignment = (
        Assignment.query
        .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
        .filter(RespostaFormulario.trabalho_id == 794)
        .first()
    )
    
    print(f'Assignment encontrado: {assignment is not None}')
    
    if assignment:
        print(f'Reviewer ID: {assignment.reviewer_id}')
        print(f'Resposta formulário ID: {assignment.resposta_formulario_id}')
        
        # Verificar o usuário revisor
        reviewer = Usuario.query.get(assignment.reviewer_id)
        if reviewer:
            print(f'Reviewer: {reviewer.nome} ({reviewer.email})')
            print(f'Tipo de usuário: {reviewer.tipo}')
    else:
        print('Nenhum assignment encontrado para o trabalho 794')
        
        # Verificar se existe resposta_formulario para este trabalho
        resposta = RespostaFormulario.query.filter_by(trabalho_id=794).first()
        print(f'Resposta formulário encontrada: {resposta is not None}')
        
        if resposta:
            print(f'Resposta formulário ID: {resposta.id}')
            
            # Verificar todos os assignments
            all_assignments = Assignment.query.all()
            print(f'Total de assignments no sistema: {len(all_assignments)}')