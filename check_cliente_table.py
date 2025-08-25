from app import create_app
from models.user import Usuario, Cliente

app = create_app()

with app.app_context():
    print("=== Verificação da Tabela Cliente ===")
    
    # Verificar se existe cliente com ID 7
    cliente = Cliente.query.filter_by(id=7).first()
    if cliente:
        print(f"✅ Cliente encontrado: {cliente.nome} (ID: {cliente.id})")
    else:
        print("❌ Cliente com ID 7 não encontrado na tabela Cliente")
    
    # Verificar todos os clientes
    clientes = Cliente.query.all()
    print(f"\nTotal de clientes na tabela: {len(clientes)}")
    for c in clientes:
        print(f"  - {c.nome} (ID: {c.id})")
    
    # Verificar usuário com ID 7
    usuario = Usuario.query.filter_by(id=7).first()
    if usuario:
        print(f"\n✅ Usuário encontrado: {usuario.nome} (ID: {usuario.id}, Tipo: {usuario.tipo})")
        
        # Verificar se existe um cliente correspondente
        cliente_correspondente = Cliente.query.filter_by(email=usuario.email).first()
        if cliente_correspondente:
            print(f"✅ Cliente correspondente encontrado: {cliente_correspondente.nome} (ID: {cliente_correspondente.id})")
        else:
            print("❌ Não existe cliente correspondente para este usuário")
            print("\n=== Criando cliente correspondente ===")
            
            try:
                from extensions import db
                novo_cliente = Cliente(
                    nome=usuario.nome,
                    email=usuario.email,
                    senha=usuario.senha,  # Usar a senha do usuário
                    ativo=True,
                    tipo='cliente'
                )
                db.session.add(novo_cliente)
                db.session.commit()
                print(f"✅ Cliente criado com sucesso: {novo_cliente.nome} (ID: {novo_cliente.id})")
            except Exception as e:
                print(f"❌ Erro ao criar cliente: {e}")
                db.session.rollback()
    
    print("\n=== Verificação concluída ===")