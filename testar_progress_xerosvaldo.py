from app import create_app
from models.review import RevisorCandidatura
from models.user import Usuario
from flask import url_for

app = create_app()
with app.app_context():
    print("=== TESTANDO ACESSO À PÁGINA PROGRESS DO XEROSVALDO ===")
    
    # Código do Xerosvaldo
    codigo_xerosvaldo = "f10d22ed"
    
    # Simular exatamente o que acontece na rota progress
    cand = RevisorCandidatura.query.filter_by(codigo=codigo_xerosvaldo).first_or_404()
    
    print(f"Candidatura encontrada:")
    print(f"ID: {cand.id}")
    print(f"Código: {cand.codigo}")
    print(f"Nome na candidatura: {cand.nome}")
    print(f"Email: {cand.email}")
    print(f"Status: {cand.status}")
    
    # Determinar o nome do revisor (exatamente como na rota)
    nome_revisor = cand.nome
    print(f"\nNome inicial (da candidatura): {nome_revisor}")
    
    if cand.status == 'aprovado':
        revisor_user = Usuario.query.filter_by(email=cand.email).first()
        print(f"Usuário encontrado: {revisor_user is not None}")
        
        if revisor_user:
            print(f"ID do usuário: {revisor_user.id}")
            print(f"Nome do usuário: {revisor_user.nome}")
            print(f"Email do usuário: {revisor_user.email}")
            
            if revisor_user.nome:
                nome_revisor = revisor_user.nome
                print(f"Nome atualizado para: {nome_revisor}")
    
    print(f"\nNome final que deveria ser exibido: {nome_revisor}")
    
    # Verificar se há outros códigos que podem estar sendo confundidos
    print("\n=== VERIFICANDO OUTROS CÓDIGOS SIMILARES ===")
    todos_codigos = RevisorCandidatura.query.all()
    
    for candidatura in todos_codigos:
        if candidatura.codigo != codigo_xerosvaldo:
            print(f"Código: {candidatura.codigo} - Nome: {candidatura.nome} - Status: {candidatura.status}")
    
    # URL que deveria ser acessada
    print(f"\nURL correta para Xerosvaldo: /revisor/progress/{codigo_xerosvaldo}")