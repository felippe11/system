from celery import Celery
from app import create_app
import os

celery = Celery(
    __name__,
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

app = create_app()

class FlaskTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)

celery.Task = FlaskTask

@celery.task
def send_email_task(*args, **kwargs):
    from services.pdf_service import enviar_email

    enviar_email(*args, **kwargs)

@celery.task
def gerar_comprovante_task(*args, **kwargs):
    from services.pdf_service import gerar_comprovante_pdf

    return gerar_comprovante_pdf(*args, **kwargs)
