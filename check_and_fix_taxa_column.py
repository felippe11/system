from app import app
from extensions import db
from sqlalchemy import text

with app.app_context():
    # Obter conexão
    conn = db.engine.connect()
    
    # Consultar informações da tabela configuracao_cliente
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'configuracao_cliente'"))
    
    print("Colunas na tabela configuracao_cliente:")
    for row in result:
        print(f"- {row[0]}: {row[1]}")
    
    # Verificar se a coluna taxa_diferenciada existe
    result = conn.execute(text("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'configuracao_cliente' AND column_name = 'taxa_diferenciada'"))
    taxa_exists = result.scalar() > 0
    
    print(f"\nA coluna taxa_diferenciada {'existe' if taxa_exists else 'NÃO existe'} na tabela.")
    
    if not taxa_exists:
        print("\nScript SQL para adicionar a coluna manualmente:")
        print("ALTER TABLE configuracao_cliente ADD COLUMN taxa_diferenciada NUMERIC(5, 2);")
        
        # Adicionar a coluna manualmente
        try:
            conn.execute(text("ALTER TABLE configuracao_cliente ADD COLUMN taxa_diferenciada NUMERIC(5, 2)"))
            conn.commit()  # Importante para confirmar a transação
            print("\nColuna taxa_diferenciada adicionada com sucesso!")
        except Exception as e:
            print(f"\nErro ao adicionar coluna: {str(e)}")
    
    conn.close()
