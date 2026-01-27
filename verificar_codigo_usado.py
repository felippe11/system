from app import create_app
from models.review import RevisorCandidatura, Assignment
from models.user import Usuario
from extensions import db

app = create_app()
with app.app_context():
    print("=== VERIFICANDO QUAL CÓDIGO ESTÁ SENDO USADO ===")
    
    # Verificar se há algum código específico sendo usado
    print("\nCódigos de candidaturas aprovadas:")
    candidaturas = RevisorCandidatura.query.filter_by(status='aprovado').all()
    
    for cand in candidaturas:
        print(f"Código: {cand.codigo} - Nome: {cand.nome} - Email: {cand.email}")
        
        # Verificar se há assignments para este revisor
        usuario = Usuario.query.filter_by(email=cand.email).first()
        if usuario:
            assignments = Assignment.query.filter_by(reviewer_id=usuario.id).all()
            print(f"  Assignments encontrados: {len(assignments)}")
            
            for assignment in assignments:
                print(f"    Assignment ID: {assignment.id} - Completed: {assignment.completed}")
    
    print("\n=== VERIFICANDO LÓGICA DA ROTA PROGRESS ===")
    
    # Simular a lógica da rota progress para o código do Xerosvaldo
    codigo_xerosvaldo = "f10d22ed"
    cand = RevisorCandidatura.query.filter_by(codigo=codigo_xerosvaldo).first()
    
    if cand:
        print(f"\nCandidatura encontrada para código {codigo_xerosvaldo}:")
        print(f"Nome na candidatura: {cand.nome}")
        print(f"Email: {cand.email}")
        print(f"Status: {cand.status}")
        
        # Simular a lógica de determinação do nome_revisor
        nome_revisor = cand.nome
        if cand.status == 'aprovado':
            revisor_user = Usuario.query.filter_by(email=cand.email).first()
            if revisor_user and revisor_user.nome:
                nome_revisor = revisor_user.nome
                print(f"Nome do usuário encontrado: {revisor_user.nome}")
            else:
                print("Usuário não encontrado ou sem nome")
        
        print(f"Nome final que seria exibido: {nome_revisor}")
    else:
        print(f"Candidatura não encontrada para código {codigo_xerosvaldo}")