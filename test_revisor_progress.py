#!/usr/bin/env python3

from app import create_app
from models.review import RevisorCandidatura, Assignment
from models.event import RespostaFormulario
from models import Usuario
from extensions import db

app = create_app()

with app.app_context():
    codigo_revisor = "f10d22ed"
    
    print(f"Testando a lógica FINAL corrigida para revisor {codigo_revisor}")
    
    # Buscar candidatura
    cand = RevisorCandidatura.query.filter_by(codigo=codigo_revisor).first()
    if not cand:
        print("Candidatura não encontrada!")
        exit(1)
    
    print(f"Candidatura encontrada: {cand.nome} - Status: {cand.status}")
    
    trabalhos_designados = []
    if cand.status == 'aprovado':
        revisor_user = Usuario.query.filter_by(email=cand.email).first()
        if revisor_user:
            print(f"Usuário revisor encontrado: {revisor_user.nome} (ID: {revisor_user.id})")
            
            # Simular a lógica CORRIGIDA da rota
            query = (
                Assignment.query
                .options(
                    db.joinedload(Assignment.resposta_formulario),
                    db.joinedload(Assignment.reviewer)
                )
                .filter_by(reviewer_id=revisor_user.id)
            )
            
            print(f"\nAssignments encontrados (SEM filtro distribution_date): {query.count()}")
            
            assignments = query.all()
            
            for assignment in assignments:
                resposta = assignment.resposta_formulario
                if not resposta:
                    print(f"Assignment {assignment.id}: SEM resposta formulário")
                    continue
                    
                print(f"\nAssignment {assignment.id}:")
                print(f"  - Resposta ID: {resposta.id}")
                print(f"  - Trabalho ID: {resposta.trabalho_id}")
                print(f"  - Deadline: {assignment.deadline}")
                print(f"  - Distribution date: {assignment.distribution_date}")
                
                # Buscar campos da resposta
                campos = {
                    rc.campo.nome: rc.valor
                    for rc in resposta.respostas_campos
                    if rc.campo and rc.campo.nome
                }
                
                titulo = campos.get("Título", "Sem título")
                categoria = campos.get("Categoria", "Sem categoria")
                
                print(f"  - Título: {titulo}")
                print(f"  - Categoria: {categoria}")
                
                trabalho = {
                    "titulo": titulo,
                    "categoria": categoria,
                    "assignment_id": assignment.id,
                    "resposta_id": resposta.id,
                    "trabalho_id": resposta.trabalho_id
                }
                trabalhos_designados.append(trabalho)
    
    print(f"\n=== RESULTADO FINAL ===")
    print(f"Total de trabalhos que serão exibidos na página: {len(trabalhos_designados)}")
    
    if trabalhos_designados:
        print("\nTrabalhos que aparecerão:")
        for i, trabalho in enumerate(trabalhos_designados, 1):
            print(f"{i}. {trabalho['titulo']} (Assignment {trabalho['assignment_id']})")
    else:
        print("NENHUM trabalho será exibido - problema ainda existe!")