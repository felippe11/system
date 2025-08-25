from app import create_app, db
from models.user import Usuario
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    print("=== Verificando usuários no banco ===")
    
    # Listar todos os usuários
    usuarios = Usuario.query.all()
    print(f"\nTotal de usuários: {len(usuarios)}")
    
    for user in usuarios:
        print(f"ID: {user.id}, Email: {user.email}, Tipo: {user.tipo}, Nome: {user.nome}")
    
    # Verificar se existe o usuário andre@teste.com
    andre = Usuario.query.filter_by(email='andre@teste.com').first()
    if andre:
        print(f"\n✓ Usuário andre@teste.com encontrado:")
        print(f"  ID: {andre.id}")
        print(f"  Nome: {andre.nome}")
        print(f"  Tipo: {andre.tipo}")
        print(f"  Ativo: {getattr(andre, 'ativo', 'N/A')}")
    else:
        print("\n✗ Usuário andre@teste.com NÃO encontrado")
        
        # Criar usuário de teste
        print("\nCriando usuário de teste...")
        novo_usuario = Usuario(
            nome='Andre Teste',
            cpf='98765432100',
            email='andre@teste.com',
            senha=generate_password_hash('123456'),
            formacao='Teste',
            tipo='cliente',
            ativo=True
        )
        
        try:
            db.session.add(novo_usuario)
            db.session.commit()
            print("✓ Usuário criado com sucesso!")
        except Exception as e:
            print(f"✗ Erro ao criar usuário: {e}")
            db.session.rollback()
    
    # Verificar usuários do tipo cliente
    clientes = Usuario.query.filter_by(tipo='cliente').all()
    print(f"\nUsuários do tipo 'cliente': {len(clientes)}")
    for cliente in clientes:
        print(f"  {cliente.email} - {cliente.nome}")