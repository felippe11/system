from app import create_app
from models.review import RevisorCandidatura
from models.user import Usuario

app = create_app()
with app.app_context():
    print("=== CANDIDATURAS DO XEROSVALDO ===")
    xerosvaldo = Usuario.query.filter_by(nome='Xerosvaldo').first()
    if xerosvaldo:
        print(f"Usuário Xerosvaldo encontrado: ID {xerosvaldo.id}, Email: {xerosvaldo.email}")
        
        # Buscar candidaturas pelo email
        candidaturas = RevisorCandidatura.query.filter_by(email=xerosvaldo.email).all()
        print(f"\nCandidaturas encontradas: {len(candidaturas)}")
        
        for cand in candidaturas:
            print(f"\nCandidatura ID: {cand.id}")
            print(f"Código: {cand.codigo}")
            print(f"Nome na candidatura: {cand.nome}")
            print(f"Email na candidatura: {cand.email}")
            print(f"Status: {cand.status}")
            print(f"Processo ID: {cand.process_id}")
    else:
        print("Usuário Xerosvaldo não encontrado")
    
    print("\n=== TODAS AS CANDIDATURAS APROVADAS ===")
    candidaturas_aprovadas = RevisorCandidatura.query.filter_by(status='aprovado').all()
    
    for cand in candidaturas_aprovadas:
        print(f"\nCandidatura ID: {cand.id}")
        print(f"Código: {cand.codigo}")
        print(f"Nome na candidatura: {cand.nome}")
        print(f"Email na candidatura: {cand.email}")
        print(f"Status: {cand.status}")
        
        # Verificar se existe usuário correspondente
        usuario = Usuario.query.filter_by(email=cand.email).first()
        if usuario:
            print(f"Usuário correspondente: ID {usuario.id}, Nome: {usuario.nome}")
        else:
            print("Nenhum usuário correspondente encontrado")