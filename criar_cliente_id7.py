from app import create_app
from models.user import Cliente
from extensions import db
from werkzeug.security import generate_password_hash

def criar_cliente_id7():
    """Cria um cliente com ID 7 para resolver o problema de autenticação."""
    
    app = create_app()
    with app.app_context():
        # Verificar se já existe um cliente com ID 7
        cliente_existente = Cliente.query.filter_by(id=7).first()
        if cliente_existente:
            print(f"Cliente ID 7 já existe: {cliente_existente.email}")
            return
        
        # Verificar se existe um cliente com o email andre@teste.com
        cliente_email = Cliente.query.filter_by(email='andre@teste.com').first()
        if cliente_email:
            print(f"Cliente com email andre@teste.com já existe com ID: {cliente_email.id}")
            # Vamos atualizar o ID deste cliente para 7
            try:
                # Primeiro, vamos verificar se podemos alterar o ID
                db.session.execute(db.text("UPDATE cliente SET id = 7 WHERE email = 'andre@teste.com'"))
                db.session.commit()
                print("ID do cliente andre@teste.com atualizado para 7")
                return
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao atualizar ID: {e}")
        
        # Criar novo cliente com ID 7
        try:
            # Inserir diretamente com ID específico
            db.session.execute(db.text("""
                INSERT INTO cliente (id, email, senha, nome, ativo, created_at) 
                VALUES (7, 'andre@teste.com', :senha, 'Andre Teste', true, NOW())
            """), {'senha': generate_password_hash('123456')})
            
            db.session.commit()
            print("Cliente ID 7 criado com sucesso!")
            print("Email: andre@teste.com")
            print("Senha: 123456")
            
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao criar cliente ID 7: {e}")
            
            # Tentar criar sem especificar ID
            try:
                novo_cliente = Cliente(
                    email='andre7@teste.com',
                    senha=generate_password_hash('123456'),
                    nome='Andre Teste ID7',
                    ativo=True
                )
                db.session.add(novo_cliente)
                db.session.commit()
                print(f"Cliente criado com ID: {novo_cliente.id}")
                print("Email: andre7@teste.com")
                print("Senha: 123456")
            except Exception as e2:
                db.session.rollback()
                print(f"Erro ao criar cliente alternativo: {e2}")

if __name__ == "__main__":
    criar_cliente_id7()