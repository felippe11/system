from app import create_app
from models.event import Evento
from models.user import Cliente
from extensions import db
from datetime import datetime

def verificar_e_criar_eventos():
    """Verifica se há eventos na base de dados e cria alguns se necessário."""
    
    app = create_app()
    with app.app_context():
        # Verificar quantos eventos existem
        total_eventos = Evento.query.count()
        print(f"Total de eventos na base de dados: {total_eventos}")
        
        # Listar todos os eventos
        eventos = Evento.query.all()
        print("\nEventos existentes:")
        for evento in eventos:
            print(f"  ID: {evento.id}, Nome: {evento.nome}, Cliente ID: {evento.cliente_id}")
        
        # Verificar clientes
        clientes = Cliente.query.all()
        print(f"\nTotal de clientes: {len(clientes)}")
        for cliente in clientes:
            print(f"  ID: {cliente.id}, Email: {cliente.email}, Nome: {getattr(cliente, 'nome', 'N/A')}")
        
        # Se não há eventos, criar alguns de teste
        if total_eventos == 0:
            print("\nNenhum evento encontrado. Criando eventos de teste...")
            
            # Pegar o primeiro cliente disponível
            cliente = Cliente.query.first()
            if not cliente:
                print("Erro: Nenhum cliente encontrado na base de dados!")
                return
            
            # Criar eventos de teste
            eventos_teste = [
                {
                    "nome": "Congresso de Tecnologia 2025",
                    "descricao": "Evento sobre as últimas tendências em tecnologia",
                    "cliente_id": cliente.id,
                    "data_inicio": datetime(2025, 9, 15),
                    "data_fim": datetime(2025, 9, 17),
                    "inscricao_gratuita": True,
                    "publico": True,
                    "status": "ativo"
                },
                {
                    "nome": "Workshop de Python",
                    "descricao": "Workshop prático de programação em Python",
                    "cliente_id": cliente.id,
                    "data_inicio": datetime(2025, 10, 5),
                    "data_fim": datetime(2025, 10, 5),
                    "inscricao_gratuita": False,
                    "publico": True,
                    "status": "ativo"
                },
                {
                    "nome": "Seminário de IA",
                    "descricao": "Seminário sobre Inteligência Artificial",
                    "cliente_id": cliente.id,
                    "data_inicio": datetime(2025, 11, 20),
                    "data_fim": datetime(2025, 11, 20),
                    "inscricao_gratuita": True,
                    "publico": True,
                    "status": "ativo"
                }
            ]
            
            for evento_data in eventos_teste:
                evento = Evento(**evento_data)
                db.session.add(evento)
                print(f"  Criado evento: {evento_data['nome']}")
            
            try:
                db.session.commit()
                print("\nEventos de teste criados com sucesso!")
            except Exception as e:
                db.session.rollback()
                print(f"\nErro ao criar eventos: {e}")
        
        # Verificar eventos do cliente específico (ID 7 do log)
        print("\n=== Verificação específica do cliente ID 7 ===")
        cliente_7 = Cliente.query.get(7)
        if cliente_7:
            eventos_cliente_7 = Evento.query.filter_by(cliente_id=7).all()
            print(f"Cliente ID 7 ({cliente_7.email}): {len(eventos_cliente_7)} eventos")
            for evento in eventos_cliente_7:
                print(f"  - {evento.nome} (ID: {evento.id})")
        else:
            print("Cliente ID 7 não encontrado")

if __name__ == "__main__":
    verificar_e_criar_eventos()