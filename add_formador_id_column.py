#!/usr/bin/env python3
"""Adiciona a coluna formador_id à tabela oficina."""

import os
import sys

from sqlalchemy import inspect, text

# Garante que conseguimos importar a aplicação
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402


def add_formador_column() -> bool:
    """Cria a coluna formador_id em oficina se ela ainda não existir."""
    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)
        columns = {col['name'] for col in inspector.get_columns('oficina')}

        if 'formador_id' in columns:
            print("✓ Coluna 'formador_id' já existe em 'oficina'. Nada a fazer.")
            return True

        try:
            print("Adicionando coluna 'formador_id' na tabela 'oficina'...")
            db.session.execute(text("ALTER TABLE oficina ADD COLUMN formador_id INTEGER"))

            # Tenta criar a constraint de chave estrangeira (pode falhar em alguns bancos).
            try:
                db.session.execute(
                    text(
                        "ALTER TABLE oficina ADD CONSTRAINT fk_oficina_formador "
                        "FOREIGN KEY(formador_id) REFERENCES ministrante(id)"
                    )
                )
                print("✓ Constraint fk_oficina_formador criada.")
            except Exception as fk_err:
                # Em bancos como SQLite o ALTER TABLE não suporta adicionar FK depois da criação.
                print(f"⚠️  Não foi possível criar a constraint automaticamente: {fk_err}")
                print("   Certifique-se de aplicar a constraint manualmente se o seu banco suportar.")

            db.session.commit()
            print("✓ Coluna 'formador_id' adicionada com sucesso!")
            return True

        except Exception as exc:  # pragma: no cover - apenas logging em caso de erro manual
            db.session.rollback()
            print(f"✗ Erro ao adicionar coluna 'formador_id': {exc}")
            return False


def main() -> None:
    print("=== Migração: adicionar coluna formador_id em oficina ===")
    sucesso = add_formador_column()
    if not sucesso:
        sys.exit(1)


if __name__ == '__main__':
    main()
