#!/usr/bin/env python3

import requests
from models.review import Assignment
from models.event import RespostaFormulario
from app import create_app

app = create_app()
with app.app_context():
    print("Verificando assignments com submission_id válidos...\n")
    
    # Buscar todos os assignments
    assignments = Assignment.query.all()
    print(f"Total de assignments encontrados: {len(assignments)}")
    
    valid_assignments = []
    
    for assignment in assignments:
        resposta = RespostaFormulario.query.get(assignment.resposta_formulario_id)
        if resposta and resposta.trabalho_id is not None:
            valid_assignments.append({
                'assignment_id': assignment.id,
                'submission_id': resposta.trabalho_id,
                'reviewer_id': assignment.reviewer_id,
                'completed': assignment.completed
            })
    
    print(f"\nAssignments com submission_id válidos: {len(valid_assignments)}")
    
    if valid_assignments:
        print("\nPrimeiros 5 assignments válidos:")
        for i, assignment in enumerate(valid_assignments[:5]):
            print(f"  {i+1}. Assignment {assignment['assignment_id']} -> Submission {assignment['submission_id']}")
        
        # Testar a rota com o primeiro assignment válido
        test_assignment = valid_assignments[0]
        url = f"http://localhost:5000/revisor/selecionar_categoria_barema/{test_assignment['submission_id']}"
        print(f"\nTestando rota corrigida: {url}")
        
        try:
            response = requests.get(url)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("✅ Rota funcionando corretamente com a correção!")
            elif response.status_code == 404:
                print("❌ Ainda retorna 404 - pode ser que o Submission não exista")
            else:
                print(f"⚠️ Status inesperado: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
    else:
        print("❌ Nenhum assignment com submission_id válido encontrado")
        print("\nVerificando alguns assignments específicos:")
        for assignment_id in [341, 342, 343, 344, 345]:
            assignment = Assignment.query.get(assignment_id)
            if assignment:
                resposta = RespostaFormulario.query.get(assignment.resposta_formulario_id)
                trabalho_id = resposta.trabalho_id if resposta else None
                print(f"  Assignment {assignment_id}: submission_id = {trabalho_id}")