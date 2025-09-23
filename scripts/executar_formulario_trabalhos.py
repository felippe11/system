#!/usr/bin/env python3
"""Create the default "Formulário de Trabalhos" if it is missing."""

import sys
import os

# Adicionar o diretório raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.formulario import ensure_formulario_trabalhos


def main() -> None:
    """Create the form inside an application context and report its ID."""
    app = create_app()
    with app.app_context():
        formulario = ensure_formulario_trabalhos()
        print(f"Formulário criado com ID: {formulario.id}")


if __name__ == "__main__":
    main()
