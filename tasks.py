import os

try:
    from celery import Celery
    from celery.signals import worker_process_init
except ImportError:  # pragma: no cover - optional dependency
    Celery = None
    worker_process_init = None

from app import create_app


if Celery:
    def create_celery() -> Celery:
        """Factory for the Celery application.

        The Flask application is created only when the worker process initializes,
        avoiding a global application instance at import time.
        """

        # Try Redis first, fallback to memory broker for development
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            # Test Redis connection
            import redis
            r = redis.from_url(redis_url)
            r.ping()
            broker_url = redis_url
            backend_url = redis_url
        except (redis.ConnectionError, redis.TimeoutError, ImportError):
            # Fallback to memory broker for development
            broker_url = "memory://"
            backend_url = "cache+memory://"
        
        celery = Celery(
            __name__,
            broker=broker_url,
            backend=backend_url,
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
else:
    celery = None

    def send_email_task(*args, **kwargs):
        """Synchronous email sending fallback."""
        from utils import enviar_email

        enviar_email(*args, **kwargs)

    def gerar_comprovante_task(*args, **kwargs):
        from services.pdf_service import gerar_comprovante_pdf

        return gerar_comprovante_pdf(*args, **kwargs)
