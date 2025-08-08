import os

from celery import Celery
from celery.signals import worker_process_init

from app import create_app


def create_celery() -> Celery:
    """Factory for the Celery application.

    The Flask application is created only when the worker process initializes,
    avoiding a global application instance at import time.
    """

    celery = Celery(
        __name__,
        broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    )

    app = None

    @worker_process_init.connect
    def init_flask_app(**_: object) -> None:
        nonlocal app
        app = create_app()

    class FlaskTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = FlaskTask
    return celery


celery = create_celery()


@celery.task
def send_email_task(*args, **kwargs):
    from utils import enviar_email

    enviar_email(*args, **kwargs)


@celery.task
def gerar_comprovante_task(*args, **kwargs):
    from services.pdf_service import gerar_comprovante_pdf

    return gerar_comprovante_pdf(*args, **kwargs)
