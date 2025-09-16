# -*- coding: utf-8 -*-
"""
Configurações específicas do servidor para prevenir broken pipe errors.

Importante: evitamos chamar eventlet.monkey_patch() aqui no import,
pois isso precisa ocorrer antes de quaisquer outros imports para ser seguro.
Como este módulo é importado no meio do boot da aplicação, pular o monkey patch
evita erros "Working outside of application/request context".
"""
import logging
import socket

# Timeout padrão de sockets (5 minutos)
socket.setdefaulttimeout(300)

def configure_server_stability():
    """Configura o servidor para maior estabilidade.

    - Evita aplicar monkey patches tardios do eventlet.
    - Ajusta logging do servidor WSGI do eventlet quando disponível.
    - Em versões do eventlet nas quais HttpProtocol.write não existe, pula o patch.
    """
    # Tentar ajustar logging do eventlet quando disponível
    try:
        import eventlet.wsgi as _evwsgi  # type: ignore
        logging.getLogger('eventlet.wsgi').setLevel(logging.WARNING)

        # Apenas aplica patch se o atributo existir nesta versão
        http_proto = getattr(_evwsgi, 'HttpProtocol', None)
        write_attr = getattr(http_proto, 'write', None) if http_proto else None

        if write_attr:
            original_write = write_attr

            def patched_write(self, data):
                try:
                    return original_write(self, data)
                except (BrokenPipeError, ConnectionError, OSError) as e:
                    if "Broken pipe" in str(e) or "Connection reset" in str(e):
                        logging.warning(f"Client disconnected: {str(e)}")
                        return
                    raise

            setattr(http_proto, 'write', patched_write)
            print("✓ Patch de HttpProtocol.write aplicado (eventlet)")
        else:
            # Sem atributo write nesta versão; seguir sem patch
            print("ℹ︎ Eventlet HttpProtocol.write indisponível; patch ignorado")
    except Exception as e:
        # Eventlet não disponível ou erro ao inspecionar; seguir sem patch
        logging.debug(f"Eventlet WSGI não disponível para patch: {e}")
        print("ℹ︎ Eventlet WSGI não patchado; prosseguindo sem alterações")

if __name__ == "__main__":
    configure_server_stability()