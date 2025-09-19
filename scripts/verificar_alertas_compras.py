#!/usr/bin/env python3
"""
Script para verificação automática de alertas críticos do sistema de compras.
Este script deve ser executado periodicamente via cron job ou task scheduler.

Uso:
    python scripts/verificar_alertas_compras.py
"""

import os
import sys
import logging
from datetime import datetime

# Adicionar o diretório raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from services.compra_notification_service import CompraNotificationService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/alertas_compras.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Função principal para verificação de alertas."""
    try:
        logger.info("Iniciando verificação automática de alertas de compras...")
        
        # Criar aplicação Flask
        app = create_app()
        
        with app.app_context():
            # Executar verificação de alertas críticos
            CompraNotificationService.verificar_alertas_criticos()
            
        logger.info("Verificação de alertas concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante verificação de alertas: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()