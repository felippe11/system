from app import create_app
from extensions import db
from models import ConfiguracaoCliente
from models.user import Usuario, Cliente
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("\n=== Teste de funcionalidades pós-migração ===")
    
    # 1. Verificar o modelo Usuario com campos MFA
    try:
        usuario = db.session.query(Usuario).first()
        if usuario is not None:
            print(f"\nConsulta ao usuário com ID {usuario.id} bem-sucedida!")
            print(f"Nome: {usuario.nome}")
            print(f"MFA habilitado: {usuario.mfa_enabled}")
            print(f"MFA secret: {'Configurado' if usuario.mfa_secret else 'Não configurado'}")
        else:
            print("Nenhum usuário encontrado no banco de dados.")
    except Exception as e:
        print(f"Erro ao consultar usuário: {str(e)}")
    
    # 2. Verificar as configurações de taxa diferenciada
    try:
        configs = db.session.query(ConfiguracaoCliente).all()
        print(f"\nEncontradas {len(configs)} configurações de clientes")
        
        for config in configs:
            cliente = db.session.query(Cliente).filter_by(id=config.cliente_id).first()
            cliente_nome = cliente.nome if cliente else "Nome não encontrado"
            print(f"\nCliente: {cliente_nome} (ID: {config.cliente_id})")
            print(f"Taxa diferenciada: {config.taxa_diferenciada}")
            print(f"Mostrar taxa ao cliente: {'Sim' if config.mostrar_taxa else 'Não'}")
    except Exception as e:
        print(f"Erro ao consultar configurações de cliente: {str(e)}")
        
    print("\n=== Teste concluído ===")
