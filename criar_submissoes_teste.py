from app import create_app
from models.review import Submission
from models.event import Evento
from extensions import db
import uuid
import secrets
from werkzeug.security import generate_password_hash

def criar_submissoes_teste():
    app = create_app()
    with app.app_context():
        # Buscar evento do cliente 2
        evento = Evento.query.filter_by(cliente_id=2).first()
        
        if not evento:
            print("Nenhum evento encontrado para cliente_id=2")
            return
        
        print(f"Criando submissões para evento: {evento.nome} (ID: {evento.id})")
        
        # Criar 3 submissões de teste
        submissoes = []
        
        for i in range(1, 4):
            locator = str(uuid.uuid4())
            raw_code = secrets.token_urlsafe(8)[:8]
            code_hash = generate_password_hash(raw_code, method='pbkdf2:sha256')
            
            submission = Submission(
                title=f'Trabalho Teste {i}',
                content=f'Conteúdo do trabalho teste número {i}',
                locator=locator,
                code_hash=code_hash,
                evento_id=evento.id
            )
            
            db.session.add(submission)
            submissoes.append((submission, raw_code))
        
        # Commit das alterações
        db.session.commit()
        
        print("\nSubmissões criadas com sucesso:")
        for submission, code in submissoes:
            print(f"- {submission.title} (Locator: {submission.locator}, Código: {code})")
        
        print(f"\nTotal: {len(submissoes)} submissões criadas")

if __name__ == "__main__":
    criar_submissoes_teste()