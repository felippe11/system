import logging
import os

logger = logging.getLogger(__name__)

logger.info(
    'MERCADOPAGO_ACCESS_TOKEN: %s',
    bool(os.getenv('MERCADOPAGO_ACCESS_TOKEN')),
)
