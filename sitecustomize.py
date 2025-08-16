import importlib
import logging

logger = logging.getLogger(__name__)

try:
    import utils  # Preload real utils package before tests may stub it
except ImportError as exc:
    logger.exception("Falha ao pré-carregar pacote utils: %s", exc)
