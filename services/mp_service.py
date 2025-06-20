import os
import logging
try:
    import mercadopago
except ImportError:  # just in case dependency missing
    mercadopago = None

_logger = logging.getLogger("payment")

# cache for the SDK instance
_sdk = None

def get_sdk():
    """Return a configured MercadoPago SDK or ``None`` if token missing."""
    global _sdk
    if _sdk is not None:
        return _sdk

    token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not token or mercadopago is None:
        _logger.warning(
            "\u26a0\ufe0f MERCADOPAGO_ACCESS_TOKEN n\u00e3o definido. Fun\u00e7\u00f5es de pagamento estar\u00e3o desativadas."
        )
        _sdk = None
    else:
        try:
            _logger.info("Inicializando SDK do Mercado Pago")
            _sdk = mercadopago.SDK(token)
            # Verificar se a SDK foi inicializada corretamente
            if _sdk:
                _logger.info("SDK do Mercado Pago inicializada com sucesso")
            else:
                _logger.error("Falha ao inicializar SDK do Mercado Pago")
        except Exception as e:
            _logger.exception(f"Erro ao inicializar SDK do Mercado Pago: {str(e)}")
            _sdk = None
    return _sdk