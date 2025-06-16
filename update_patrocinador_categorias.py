#!/usr/bin/env python3
"""Atualiza categorias de patrocinadores para usar acentuação correta."""
from app import create_app
from extensions import db
from models import Patrocinador

CATEGORIA_MAP = {
    "Realizacao": "Realização",
    "Patrocinio": "Patrocínio",
    "Organizacao": "Organização",
    "realizacao": "Realização",
    "patrocinio": "Patrocínio",
    "organizacao": "Organização",
}


def main():
    app = create_app()
    with app.app_context():
        patrocinadores = Patrocinador.query.filter(
            Patrocinador.categoria.in_(CATEGORIA_MAP.keys())
        ).all()
        count = 0
        for pat in patrocinadores:
            pat.categoria = CATEGORIA_MAP.get(pat.categoria, pat.categoria)
            count += 1
        if count:
            db.session.commit()
        print(f"Categorias atualizadas: {count}")


if __name__ == "__main__":
    main()
