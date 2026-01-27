from app import create_app
from models.review import Assignment, RevisorCandidatura, Submission
from models.event import RespostaFormulario
from models.user import Usuario
from sqlalchemy.orm import joinedload

app = create_app()

with app.app_context():
    # Buscar o revisor específico f10d22ed
    codigo_revisor = 'f10d22ed'
    print(f"Buscando revisor com código: {codigo_revisor}")
    
    candidatura = RevisorCandidatura.query.filter_by(codigo=codigo_revisor).first()
    if not candidatura:
        print("Candidatura não encontrada!")
        exit()
    
    print(f"Candidatura encontrada: {candidatura.nome} - {candidatura.email}")
    print(f"Status: {candidatura.status}")
    
    # Buscar o usuário associado
    usuario = Usuario.query.filter_by(email=candidatura.email).first()
    if not usuario:
        print("Usuário não encontrado!")
        exit()
    
    print(f"Usuário encontrado: {usuario.nome} (ID: {usuario.id})")
    
    # Buscar assignments para este revisor
    print("\n=== ASSIGNMENTS PARA ESTE REVISOR ===")
    assignments = Assignment.query.filter_by(reviewer_id=usuario.id).all()
    print(f"Total de assignments: {len(assignments)}")
    
    for assignment in assignments[:10]:  # Primeiros 10
        print(f"Assignment ID: {assignment.id}")
        print(f"  Reviewer ID: {assignment.reviewer_id}")
        print(f"  Resposta Formulário ID: {assignment.resposta_formulario_id}")
        
        # Buscar a resposta do formulário
        resposta = RespostaFormulario.query.get(assignment.resposta_formulario_id)
        if resposta:
            print(f"  Resposta encontrada: Evento ID {resposta.evento_id}")
            print(f"  Usuário ID: {resposta.usuario_id}")
            print(f"  Trabalho ID: {resposta.trabalho_id}")
            print(f"  Status: {resposta.status_avaliacao}")
            
            # Buscar o trabalho associado
            if resposta.trabalho_id:
                submission = Submission.query.get(resposta.trabalho_id)
                if submission:
                    print(f"  Submission encontrada: {submission.title}")
                else:
                    print(f"  Nenhuma submission encontrada para trabalho ID {resposta.trabalho_id}")
            else:
                print(f"  Nenhum trabalho associado à resposta {resposta.id}")
        else:
            print(f"  Resposta não encontrada para ID {assignment.resposta_formulario_id}")
        print("---")
    
    print("\n=== RESUMO ===")
    print(f"O revisor {codigo_revisor} tem {len(assignments)} assignments com trabalhos válidos:")
    for assignment in assignments:
        resposta = RespostaFormulario.query.get(assignment.resposta_formulario_id)
        if resposta and resposta.trabalho_id:
            submission = Submission.query.get(resposta.trabalho_id)
            if submission:
                print(f"- {submission.title}")