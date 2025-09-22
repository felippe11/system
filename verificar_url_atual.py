from app import create_app
from models.review import RevisorCandidatura
from models.user import Usuario
from models.avaliacao import AvaliacaoBarema

app = create_app()

with app.app_context():
    print("=== VERIFICANDO TODAS AS CANDIDATURAS APROVADAS ===")
    candidaturas = RevisorCandidatura.query.filter_by(status='aprovado').all()
    
    for cand in candidaturas:
        print(f"\nCandidatura ID: {cand.id}")
        print(f"Código: {cand.codigo}")
        print(f"Nome: {cand.nome}")
        print(f"Email: {cand.email}")
        print(f"Status: {cand.status}")
        print(f"URL: /revisor/progress/{cand.codigo}")
        
        # Verificar se há usuário correspondente
        if cand.status == 'aprovado':
            revisor_user = Usuario.query.filter_by(email=cand.email).first()
            if revisor_user:
                print(f"Usuário encontrado: {revisor_user.nome} (ID: {revisor_user.id})")
            else:
                print("Usuário não encontrado")
    
    print("\n=== VERIFICANDO AVALIAÇÕES RECENTES ===")
    avaliacoes = AvaliacaoBarema.query.order_by(AvaliacaoBarema.id.desc()).limit(5).all()
    
    for av in avaliacoes:
        print(f"\nAvaliação ID: {av.id}")
        print(f"Revisor ID: {av.revisor_id}")
        print(f"Nome do revisor na avaliação: {av.nome_revisor}")
        print(f"Trabalho ID: {av.trabalho_id}")
        
        # Verificar qual usuário tem esse ID
        if av.revisor_id:
            user = Usuario.query.get(av.revisor_id)
            if user:
                print(f"Nome real do usuário ID {av.revisor_id}: {user.nome}")
    
    print("\n=== DICA PARA O USUÁRIO ===")
    print("Se você está vendo um nome incorreto, verifique:")
    print("1. Se está acessando a URL correta: /revisor/progress/f10d22ed (para Xerosvaldo)")
    print("2. Se não há cache do navegador")
    print("3. Se não está confundindo com outra candidatura")