from app import create_app
from models.review import Assignment, RevisorCandidatura
from models.event import RespostaFormulario
from models.user import Usuario

app = create_app()
with app.app_context():
    # Verificar trabalhos cadastrados
    trabalhos = RespostaFormulario.query.all()
    print(f'Total de trabalhos cadastrados: {len(trabalhos)}')
    
    if trabalhos:
        print('\nPrimeiros 5 trabalhos:')
        for trabalho in trabalhos[:5]:
            print(f'ID: {trabalho.id}, Trabalho ID: {trabalho.trabalho_id}, Evento ID: {trabalho.evento_id}')
    
    # Verificar usuários revisores
    revisores = Usuario.query.filter_by(tipo='revisor').all()
    print(f'\nTotal de revisores: {len(revisores)}')
    
    if revisores:
        print('\nPrimeiros 3 revisores:')
        for revisor in revisores[:3]:
            print(f'ID: {revisor.id}, Nome: {revisor.nome}, Email: {revisor.email}')
    
    # Verificar candidaturas aprovadas
    candidaturas = RevisorCandidatura.query.filter_by(status='aprovado').all()
    print(f'\nTotal de candidaturas aprovadas: {len(candidaturas)}')
    
    if candidaturas:
        print('\nPrimeiras 3 candidaturas aprovadas:')
        for cand in candidaturas[:3]:
            print(f'Código: {cand.codigo}, Nome: {cand.nome}, Email: {cand.email}')
            # Verificar se existe usuário correspondente
            usuario = Usuario.query.filter_by(email=cand.email).first()
            if usuario:
                print(f'  -> Usuário encontrado: {usuario.nome} (tipo: {usuario.tipo})')
            else:
                print(f'  -> Usuário NÃO encontrado para email {cand.email}')
    
    # Verificar assignments
    assignments = Assignment.query.all()
    print(f'\nTotal de assignments: {len(assignments)}')
    
    if assignments:
        print('\nPrimeiros 3 assignments:')
        for assignment in assignments[:3]:
            print(f'ID: {assignment.id}, Reviewer ID: {assignment.reviewer_id}, Resposta ID: {assignment.resposta_formulario_id}')