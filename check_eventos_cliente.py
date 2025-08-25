from app import create_app
from models.user import Usuario, Cliente
from models.event import Evento

app = create_app()

with app.app_context():
    print("=== Verificação de Eventos do Cliente ===\n")
    
    # Buscar cliente por ID (assumindo que o usuário logado tem ID 7)
    usuario = Usuario.query.filter_by(id=7, tipo='cliente').first()
    cliente = Cliente.query.filter_by(email=usuario.email).first() if usuario else None
    if not cliente:
        print("❌ Cliente não encontrado")
        exit(1)
    
    print(f"Cliente: {cliente.nome} (ID: {cliente.id})")
    
    # Buscar eventos do cliente
    eventos = Evento.query.filter_by(cliente_id=cliente.id).all()
    print(f"\nEventos encontrados: {len(eventos)}")
    
    if eventos:
        for i, evento in enumerate(eventos, 1):
            print(f"  {i}. {evento.nome} (ID: {evento.id})")
            print(f"     - Status: {getattr(evento, 'status', 'N/A')}")
            print(f"     - Descrição: {getattr(evento, 'descricao', 'N/A')}")
            print(f"     - Data criação: {getattr(evento, 'data_criacao', 'N/A')}")
    else:
        print("\n❌ Nenhum evento encontrado para este cliente")
        print("\n=== Criando evento de teste ===\n")
        
        # Criar um evento de teste
        novo_evento = Evento(
            cliente_id=cliente.id,  # ID do cliente correto
            nome="Evento de Teste",
            descricao="Evento criado para testar o select",
            status="ativo"
        )
        
        try:
            from extensions import db
            db.session.add(novo_evento)
            db.session.commit()
            print(f"✓ Evento criado: {novo_evento.nome} (ID: {novo_evento.id})")
            
            # Verificar novamente
            eventos = Evento.query.filter_by(cliente_id=cliente.id).all()
            print(f"\nEventos após criação: {len(eventos)}")
            for i, evento in enumerate(eventos, 1):
                print(f"  {i}. {evento.nome} (ID: {evento.id})")
                
        except Exception as e:
            print(f"❌ Erro ao criar evento: {e}")
            db.session.rollback()

print("\n=== Verificação concluída ===")