from app import create_app
from models.event import Evento
from models.user import Cliente
from extensions import db
from datetime import datetime

def criar_eventos_para_cliente4():
    """Cria eventos para o cliente ID 4 (andre@teste.com)."""
    
    app = create_app()
    with app.app_context():
        # Verificar se o cliente ID 4 existe
        cliente = Cliente.query.filter_by(id=4).first()
        if not cliente:
            print("Erro: Cliente ID 4 não encontrado!")
            return
        
        print(f"Cliente encontrado: ID {cliente.id}, Email: {cliente.email}")
        
        # Verificar eventos existentes do cliente
        eventos_existentes = Evento.query.filter_by(cliente_id=4).all()
        print(f"Eventos existentes do cliente: {len(eventos_existentes)}")
        
        # Criar eventos de teste para o cliente ID 4
        eventos_teste = [
            {
                "nome": "Congresso de Tecnologia 2025",
                "descricao": "Evento sobre as últimas tendências em tecnologia",
                "cliente_id": 4,
                "data_inicio": datetime(2025, 9, 15),
                "data_fim": datetime(2025, 9, 17),
                "inscricao_gratuita": True,
                "publico": True,
                "status": "ativo",
                "submissao_aberta": True
            },
            {
                "nome": "Workshop de Python",
                "descricao": "Workshop prático de programação em Python",
                "cliente_id": 4,
                "data_inicio": datetime(2025, 10, 5),
                "data_fim": datetime(2025, 10, 5),
                "inscricao_gratuita": False,
                "publico": True,
                "status": "ativo",
                "submissao_aberta": True
            },
            {
                "nome": "Seminário de IA",
                "descricao": "Seminário sobre Inteligência Artificial",
                "cliente_id": 4,
                "data_inicio": datetime(2025, 11, 20),
                "data_fim": datetime(2025, 11, 20),
                "inscricao_gratuita": True,
                "publico": True,
                "status": "ativo",
                "submissao_aberta": True
            }
        ]
        
        print("\nCriando eventos para o cliente ID 4...")
        for evento_data in eventos_teste:
            evento = Evento(**evento_data)
            db.session.add(evento)
            print(f"  Criado evento: {evento_data['nome']}")
        
        try:
            db.session.commit()
            print("\nEventos criados com sucesso!")
            
            # Verificar eventos após criação
            eventos_apos = Evento.query.filter_by(cliente_id=4).all()
            print(f"\nTotal de eventos do cliente ID 4 após criação: {len(eventos_apos)}")
            for evento in eventos_apos:
                print(f"  - {evento.nome} (ID: {evento.id})")
                
        except Exception as e:
            db.session.rollback()
            print(f"\nErro ao criar eventos: {e}")

if __name__ == "__main__":
    criar_eventos_para_cliente4()