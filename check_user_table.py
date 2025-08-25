from app import create_app
from models.user import Usuario, Cliente, Ministrante

app = create_app()

with app.app_context():
    print("=== Verificação de Tabelas de Usuário ===\n")
    
    email = 'andre@teste.com'
    
    # Verificar na tabela Usuario
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario:
        print(f"✓ Encontrado na tabela Usuario:")
        print(f"  - ID: {usuario.id}")
        print(f"  - Nome: {usuario.nome}")
        print(f"  - Tipo: {usuario.tipo}")
        print(f"  - Ativo: {getattr(usuario, 'ativo', 'N/A')}")
    else:
        print("❌ NÃO encontrado na tabela Usuario")
    
    # Verificar na tabela Cliente
    cliente = Cliente.query.filter_by(email=email).first()
    if cliente:
        print(f"\n✓ Encontrado na tabela Cliente:")
        print(f"  - ID: {cliente.id}")
        print(f"  - Nome: {cliente.nome}")
        print(f"  - Ativo: {cliente.ativo}")
    else:
        print("\n❌ NÃO encontrado na tabela Cliente")
    
    # Verificar na tabela Ministrante
    ministrante = Ministrante.query.filter_by(email=email).first()
    if ministrante:
        print(f"\n✓ Encontrado na tabela Ministrante:")
        print(f"  - ID: {ministrante.id}")
        print(f"  - Nome: {ministrante.nome}")
    else:
        print("\n❌ NÃO encontrado na tabela Ministrante")
    
    # Verificar qual tabela usar para o login
    print("\n=== Recomendação ===\n")
    if usuario and usuario.tipo == 'cliente':
        print("O usuário está na tabela Usuario com tipo 'cliente'")
        print("Para acessar /get_eventos_cliente, deve usar a tabela Usuario")
    elif cliente:
        print("O usuário está na tabela Cliente")
        print("Para acessar /get_eventos_cliente, deve usar a tabela Cliente")
    else:
        print("Usuário não encontrado em nenhuma tabela apropriada")

print("\n=== Verificação concluída ===")